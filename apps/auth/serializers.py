from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.auth.helpers import normalize_indian_phone

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
        validated_data["username"] = validated_data["email"]
        validated_data["total_credit"] = 1
        validated_data["used_credit"] = 0
        validated_data["left_credit"] = 1
        validated_data["expired_credit"] = 0
        validated_data["credit_expire_date"] = timezone.localdate() + timedelta(days=7)
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
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
            "whatsapp_number",
            "instagram_url",
            "facebook_url",
            "total_credit",
            "used_credit",
            "left_credit",
            "expired_credit",
            "credit_expire_date",
            "created_at",
            "updated_at",
            "updated_by",
        )


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
            "total_credit",
            "used_credit",
            "left_credit",
            "expired_credit",
            "credit_expire_date",
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
        )
        extra_kwargs = {
            "whatsapp_number": {"required": False, "allow_blank": True},
            "instagram_url": {"required": False, "allow_blank": True},
            "facebook_url": {"required": False, "allow_blank": True},
        }

    def validate_whatsapp_number(self, value):
        number = (value or "").strip()
        if not number:
            return ""
        return normalize_indian_phone(number)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one of whatsapp_number, instagram_url, facebook_url.")
        return attrs

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            instance.updated_by = request.user.user_id
        return super().update(instance, validated_data)
