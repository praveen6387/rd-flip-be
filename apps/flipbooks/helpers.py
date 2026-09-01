import secrets
import string

from django.utils import timezone
from rest_framework import serializers

FLIP_ID_ALPHABET = string.ascii_letters + string.digits
FLIP_ID_LENGTH = 10


def first_non_empty(*values) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def generate_flip_id() -> str:
    return "".join(secrets.choice(FLIP_ID_ALPHABET) for _ in range(FLIP_ID_LENGTH))


def unique_flip_id() -> str:
    from rd_flip_be.models import Flipbook

    for _ in range(20):
        code = generate_flip_id()
        if not Flipbook.objects.filter(flip_id=code).exists():
            return code
    raise RuntimeError("Could not generate a unique flip_id")


def validate_user_credits(user) -> None:
    """Raise ValidationError if the user cannot spend 1 credit on a flipbook."""
    today = timezone.localdate()

    if user.credit_expire_date and today > user.credit_expire_date:
        raise serializers.ValidationError(
            "Your credits have expired. Please renew to create a flipbook."
        )

    if (user.left_credit or 0) < 1:
        raise serializers.ValidationError(
            "You do not have enough credits to create a flipbook."
        )


def deduct_user_credit(user) -> None:
    user.used_credit = (user.used_credit or 0) + 1
    user.left_credit = (user.left_credit or 0) - 1
    user.updated_by = user.user_id
    user.save(update_fields=["used_credit", "left_credit", "updated_by", "updated_at"])
