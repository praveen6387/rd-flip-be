from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.auth.helpers import normalize_indian_phone

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "password",
            "studio_name",
        )
        extra_kwargs = {
            "studio_name": {"required": False, "allow_blank": True},
        }

    def resolve_signup_email(self, email: str, phone: str) -> str:
        """
        Use provided email if present.
        Otherwise build email from phone: {10digit}@gmail.com
        """
        email = (email or "").strip().lower()
        if email:
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError(
                    "A user with this email already exists."
                )
            return email

        email = f"{phone[-10:]}@gmail.com"
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "Generated email from phone is already in use."
            )
        return email

    def validate_phone(self, value):
        phone = normalize_indian_phone(value)
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("A user with this phone already exists.")
        return phone

    def validate_email(self, value):
        phone = normalize_indian_phone(self.initial_data.get("phone", ""))
        return self.resolve_signup_email(value, phone)

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data["plan"] = "studio"
        validated_data["username"] = validated_data["email"]
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user


class SignupResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "studio_name",
            "plan",
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
