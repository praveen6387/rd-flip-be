import secrets
import string
from datetime import timedelta

from django.utils import timezone
from rd_flip_be.credits import create_credit_transaction
from rest_framework import serializers

FLIP_ID_ALPHABET = string.ascii_letters + string.digits
FLIP_ID_LENGTH = 10
FREE_FLIPBOOK_LIFETIME_DAYS = 30


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


def has_active_user_plan(user) -> bool:
    """True when the user has a paid UserPlan that is still active."""
    from rd_flip_be.models import UserPlan

    return UserPlan.objects.filter(
        user=user,
        status="active",
        expiry_date__gt=timezone.now(),
    ).exists()


def resolve_active_until(user):
    """
    Free (no active plan) flipbooks expire after 30 days.
    Paid-plan flipbooks have no fixed expiry (active_until stays null).
    """
    if has_active_user_plan(user):
        return None
    return timezone.now() + timedelta(days=FREE_FLIPBOOK_LIFETIME_DAYS)


def validate_user_credits(user) -> None:
    """Raise ValidationError if the user cannot spend 1 credit on a flipbook."""
    today = timezone.localdate()

    if user.credit_expire_date and today > user.credit_expire_date:
        raise serializers.ValidationError("Your credits have expired. Please renew to create a flipbook.")

    if (user.left_credit or 0) < 1:
        raise serializers.ValidationError("You do not have enough credits to create a flipbook.")


def deduct_user_credit(user, flipbook=None) -> None:

    user.used_credit = (user.used_credit or 0) + 1
    user.left_credit = (user.left_credit or 0) - 1
    user.updated_by = user.user_id
    user.save(update_fields=["used_credit", "left_credit", "updated_by", "updated_at"])
    create_credit_transaction(
        user=user,
        credit_type="usage",
        credits=-1,
        flipbook=flipbook,
        description=(
            f"Credit used to create flipbook {flipbook.flip_id}"
            if flipbook is not None
            else "Credit used to create flipbook"
        ),
        created_by=user.user_id,
    )
