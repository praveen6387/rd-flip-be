import hashlib
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import serializers

RESET_TOKEN_TTL_MINUTES = 5


def normalize_indian_phone(value: str) -> str:
    """
    Validate an Indian mobile number and return it as +91XXXXXXXXXX.
    If +91 is already present, it is kept (not duplicated).
    """
    raw = (value or "").strip()
    if not raw:
        raise serializers.ValidationError("Phone number is required.")

    digits = re.sub(r"\D", "", raw)

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    if len(digits) != 10 or digits[0] not in "6789":
        raise serializers.ValidationError(
            "Enter a valid 10-digit Indian mobile number."
        )

    return f"+91{digits}"


def verify_current_password(user, current_password: str) -> None:
    if not user.check_password(current_password):
        raise serializers.ValidationError("Current password is incorrect.")


def set_user_password(user, new_password: str):
    user.set_password(new_password)
    user.updated_by = user.user_id
    user.save(update_fields=["password", "updated_by", "updated_at"])
    return user


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_password_reset_token(user) -> str:
    from rd_flip_be.models import PasswordResetToken

    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    raw_token = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_reset_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    )
    return raw_token


def build_password_reset_link(raw_token: str) -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return f"{base}/reset-password?token={raw_token}"


def send_password_reset_email(user, raw_token: str) -> None:
    link = build_password_reset_link(raw_token)
    send_mail(
        subject="Reset your RD Flip password",
        message=(
            f"Hi {user.first_name or 'there'},\n\n"
            "Use this link to reset your password. "
            f"It expires in {RESET_TOKEN_TTL_MINUTES} minutes.\n\n"
            f"{link}\n\n"
            "If you did not request this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def get_valid_reset_token(raw_token: str):
    from rd_flip_be.models import PasswordResetToken

    token = (
        PasswordResetToken.objects.select_related("user")
        .filter(
            token_hash=hash_reset_token(raw_token),
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .first()
    )
    if token is None:
        raise serializers.ValidationError("Invalid or expired reset token.")
    return token
