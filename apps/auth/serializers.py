from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from apps.flipbooks.s3 import canonical_image_url, presign_image_url
from apps.auth.helpers import (
    create_password_reset_token,
    get_valid_reset_token,
    normalize_indian_phone,
    send_password_reset_email,
    set_user_password,
    verify_current_password,
)
from rd_flip_be.models import CreditTransaction, Flipbook, Order, PaymentTransaction, UserPlan
from rd_flip_be.welcome import grant_welcome_plan

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "dob",
            "email",
            "phone",
            "password",
            "studio_name",
        )
        extra_kwargs = {
            "studio_name": {"required": False, "allow_blank": True},
            "dob": {"required": False, "allow_null": True},
        }

    def validate_phone(self, value):
        phone = normalize_indian_phone(value)
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("A user with this phone already exists.")
        return phone

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if not email:
            raise serializers.ValidationError("Email is required.")
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data["plan"] = "studio"
        validated_data["role"] = "studio"
        validated_data["username"] = validated_data["email"]

        with transaction.atomic():
            user = super().create(validated_data)
            user.set_password(password)
            user.save()
            grant_welcome_plan(user)
        return user


PRODUCT_BALANCE_LABELS = {
    "flipbook": "Flipbook",
    "photo_selection": "Photo Selection",
    "all": "All",
}
PRODUCT_BALANCE_ORDER = {"flipbook": 0, "photo_selection": 1, "all": 2}


class UserProfileSerializer(serializers.ModelSerializer):
    total_view_count = serializers.SerializerMethodField()
    total_like_count = serializers.SerializerMethodField()
    active_balances = serializers.SerializerMethodField()
    watermark_logo_preview = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "dob",
            "email",
            "phone",
            "studio_name",
            "plan",
            "role",
            "whatsapp_number",
            "instagram_url",
            "facebook_url",
            "watermark_enabled",
            "watermark_text",
            "watermark_position",
            "watermark_opacity",
            "watermark_include_logo",
            "watermark_logo_url",
            "watermark_logo_preview",
            "active_balances",
            "total_view_count",
            "total_like_count",
            "created_at",
            "updated_at",
            "updated_by",
        )
        read_only_fields = ("role",)

    def _engagement_totals(self, user):
        cached = getattr(user, "_engagement_totals", None)
        if cached is None:
            totals = user.flipbooks.filter(is_active=True).aggregate(
                views=Sum("view_count"),
                likes=Sum("like_count"),
            )
            cached = {
                "views": totals["views"] or 0,
                "likes": totals["likes"] or 0,
            }
            user._engagement_totals = cached
        return cached

    def get_watermark_logo_preview(self, user):
        url = getattr(user, "watermark_logo_url", "")
        if not isinstance(url, str) or not url.strip():
            return ""
        return presign_image_url(url) or ""

    def get_total_view_count(self, user):
        return self._engagement_totals(user)["views"]

    def get_total_like_count(self, user):
        return self._engagement_totals(user)["likes"]

    def get_active_balances(self, user):
        """
        One balance per active plan. Flipbook and Photo Selection stay separate.
        An All plan is a single shared balance. Welcome credits are the free Flipbook plan.
        """
        now = timezone.now()
        rows = user.user_plans.select_related("plan").filter(
            status="active",
            expiry_date__gt=now,
        )
        balances = []
        for row in rows:
            product = row.plan.product
            total = int(row.credits_total or 0)
            used = int(row.credits_used or 0)
            label = (
                "Welcome"
                if row.plan.price == 0
                else PRODUCT_BALANCE_LABELS.get(product, product)
            )
            balances.append(
                {
                    "product": product,
                    "label": label,
                    "plan_name": row.plan.name,
                    "plan_type": row.plan.plan_type,
                    "features": list(row.plan.features or []),
                    "credits_left": max(0, total - used),
                    "credits_used": used,
                    "credits_expired": 0,
                    "credits_total": total,
                    "expiry_date": timezone.localtime(row.expiry_date).date().isoformat(),
                }
            )
        balances.sort(key=lambda item: PRODUCT_BALANCE_ORDER.get(item["product"], 9))
        return balances


class AdminUserCreditTransactionSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id", read_only=True, allow_null=True)
    order_name = serializers.CharField(source="order.order_name", read_only=True, allow_null=True)
    flipbook_id = serializers.IntegerField(source="flipbook.id", read_only=True, allow_null=True)
    flipbook_title = serializers.CharField(source="flipbook.title", read_only=True, allow_null=True)

    class Meta:
        model = CreditTransaction
        fields = (
            "id",
            "credit_type",
            "credits",
            "order_id",
            "order_name",
            "flipbook_id",
            "flipbook_title",
            "expiry_date",
            "description",
            "created_at",
        )


class AdminUserOrderSerializer(serializers.ModelSerializer):
    plan_id = serializers.IntegerField(source="plan.id", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_type = serializers.CharField(source="plan.plan_type", read_only=True)
    plan_product = serializers.CharField(source="plan.product", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_name",
            "plan_id",
            "plan_name",
            "plan_type",
            "plan_product",
            "amount",
            "payment_status",
            "gateway_order_id",
            "created_at",
        )


class AdminUserPlanSerializer(serializers.ModelSerializer):
    plan_id = serializers.IntegerField(source="plan.id", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_type = serializers.CharField(source="plan.plan_type", read_only=True)
    plan_price = serializers.DecimalField(
        source="plan.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    plan_product = serializers.CharField(source="plan.product", read_only=True)
    plan_credit = serializers.IntegerField(source="plan.credit", read_only=True)
    validity_days = serializers.IntegerField(source="plan.validity_days", read_only=True)
    credits_left = serializers.SerializerMethodField()

    class Meta:
        model = UserPlan
        fields = (
            "id",
            "plan_id",
            "plan_name",
            "plan_type",
            "plan_product",
            "plan_price",
            "plan_credit",
            "credits_total",
            "credits_used",
            "credits_left",
            "validity_days",
            "start_date",
            "expiry_date",
            "status",
            "created_at",
        )

    def get_credits_left(self, obj):
        return max(0, int(obj.credits_total or 0) - int(obj.credits_used or 0))


class AdminUserPaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    order_name = serializers.CharField(source="order.order_name", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            "id",
            "order_id",
            "order_name",
            "gateway_payment_id",
            "amount",
            "payment_status",
            "payment_method",
            "created_at",
        )


class AdminUserFlipbookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flipbook
        fields = (
            "id",
            "title",
            "flip_id",
            "total_pages",
            "view_count",
            "like_count",
            "is_active",
            "active_until",
            "created_at",
        )


class AdminUserListSerializer(serializers.ModelSerializer):
    credit_transactions = AdminUserCreditTransactionSerializer(many=True, read_only=True)
    orders = AdminUserOrderSerializer(many=True, read_only=True)
    user_plans = AdminUserPlanSerializer(many=True, read_only=True)
    flipbooks = AdminUserFlipbookSerializer(many=True, read_only=True)
    payments = serializers.SerializerMethodField()
    total_view_count = serializers.IntegerField(read_only=True)
    total_like_count = serializers.IntegerField(read_only=True)
    flipbook_count = serializers.IntegerField(read_only=True)
    photo_selection_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "dob",
            "email",
            "phone",
            "studio_name",
            "whatsapp_number",
            "instagram_url",
            "facebook_url",
            "plan",
            "role",
            "is_active",
            "flipbook_count",
            "photo_selection_count",
            "total_view_count",
            "total_like_count",
            "created_at",
            "updated_at",
            "flipbooks",
            "credit_transactions",
            "orders",
            "user_plans",
            "payments",
        )

    def get_photo_selection_count(self, user):
        return user.photo_selections.count()

    def get_payments(self, user):
        payments = []
        for order in user.orders.all():
            payments.extend(list(order.payment_transactions.all()))
        payments.sort(key=lambda payment: payment.created_at, reverse=True)
        return AdminUserPaymentSerializer(payments, many=True).data


class SignupResponseSerializer(UserProfileSerializer):
    class Meta(UserProfileSerializer.Meta):
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "dob",
            "email",
            "phone",
            "studio_name",
            "plan",
            "role",
            "created_at",
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    password = serializers.CharField(write_only=True, max_length=128)

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip().lower()
        phone = (attrs.get("phone") or "").strip()
        password = attrs.get("password") or ""

        if not email and not phone:
            raise serializers.ValidationError("Provide email or phone to login.")

        user = None
        if phone:
            phone = normalize_indian_phone(phone)
            user = User.objects.filter(phone=phone).first()
        elif email:
            user = User.objects.filter(email=email).first()

        if user is None or not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        attrs["user"] = user
        return attrs


class UpdateSocialLinksSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "whatsapp_number",
            "instagram_url",
            "facebook_url",
            "watermark_enabled",
            "watermark_text",
            "watermark_position",
            "watermark_opacity",
            "watermark_include_logo",
            "watermark_logo_url",
        )
        extra_kwargs = {
            "whatsapp_number": {"required": False, "allow_blank": True},
            "instagram_url": {"required": False, "allow_blank": True},
            "facebook_url": {"required": False, "allow_blank": True},
            "watermark_enabled": {"required": False},
            "watermark_text": {"required": False, "allow_blank": True},
            "watermark_position": {"required": False, "allow_blank": True},
            "watermark_opacity": {"required": False},
            "watermark_include_logo": {"required": False},
            "watermark_logo_url": {"required": False, "allow_blank": True},
        }

    def validate_whatsapp_number(self, value):
        number = (value or "").strip()
        if not number:
            return ""
        return normalize_indian_phone(number)

    def validate_watermark_text(self, value):
        return (value or "").strip()[:120]

    def validate_watermark_position(self, value):
        position = (value or "bottom-right").strip()
        if position not in {"bottom-right", "bottom-left", "top-right", "top-left", "center", "diagonal"}:
            raise serializers.ValidationError("Choose a watermark position.")
        return position

    def validate_watermark_opacity(self, value):
        opacity = float(value)
        if opacity < 0.15 or opacity > 0.95:
            raise serializers.ValidationError("Watermark opacity must be between 15% and 95%.")
        return opacity

    def validate_watermark_logo_url(self, value):
        raw = canonical_image_url(value or "")
        if not raw:
            return ""
        user = self.instance or getattr(self.context.get("request"), "user", None)
        user_id = getattr(user, "user_id", "")
        bucket = settings.AWS_S3_BUCKET
        region = settings.AWS_S3_REGION
        prefix = f"https://{bucket}.s3.{region}.amazonaws.com/studio-logo/{user_id}/"
        name = raw[len(prefix):] if raw.startswith(prefix) else ""
        if not bucket or not user_id or not name or "/" in name or name in {".", ".."}:
            raise serializers.ValidationError("Upload the studio logo again.")
        return raw

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide a profile field to update.")
        logo = attrs.get("watermark_logo_url", getattr(self.instance, "watermark_logo_url", ""))
        include = attrs.get("watermark_include_logo", getattr(self.instance, "watermark_include_logo", False))
        if include and not logo:
            attrs["watermark_include_logo"] = False
        return attrs

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            instance.updated_by = request.user.user_id
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        max_length=128,
        error_messages={
            "blank": "Current password may not be blank.",
            "required": "Current password is required.",
        },
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        error_messages={
            "blank": "New password may not be blank.",
            "required": "New password is required.",
            "min_length": "New password must be at least 8 characters.",
        },
    )

    def validate_current_password(self, value):
        user = self.context["request"].user
        verify_current_password(user, value)
        return value

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                "New password must be different from the current password."
            )

        return attrs

    def save(self, **kwargs):
        return set_user_password(
            self.context["request"].user,
            self.validated_data["new_password"],
        )


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={
            "blank": "Email may not be blank.",
            "required": "Email is required.",
            "invalid": "Enter a valid email.",
        }
    )

    def validate_email(self, value):
        email = (value or "").strip().lower()
        user = User.objects.filter(email=email).first()
        if user is None:
            raise serializers.ValidationError("No account found with this email.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        self.context["reset_user"] = user
        return email

    def save(self, **kwargs):
        user = self.context["reset_user"]
        raw_token = create_password_reset_token(user)
        send_password_reset_email(user, raw_token)
        return user


class ResetPasswordSerializer(serializers.Serializer):
    password_reset_token = serializers.CharField(
        write_only=True,
        error_messages={
            "blank": "Password reset token may not be blank.",
            "required": "Password reset token is required.",
        },
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        error_messages={
            "blank": "New password may not be blank.",
            "required": "New password is required.",
            "min_length": "New password must be at least 8 characters.",
        },
    )

    def validate_password_reset_token(self, value):
        token = get_valid_reset_token((value or "").strip())
        self.context["reset_token"] = token
        return value

    def validate(self, attrs):
        user = self.context["reset_token"].user

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        return attrs

    def save(self, **kwargs):
        token = self.context["reset_token"]
        user = set_user_password(token.user, self.validated_data["new_password"])
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return user
