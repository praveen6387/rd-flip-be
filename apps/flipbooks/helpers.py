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


def active_flipbook_plans(user):
    """Active, unexpired Flipbook and All plans. Photo Selection is not included."""
    from rd_flip_be.models import UserPlan

    return UserPlan.objects.select_related("plan").filter(
        user=user,
        status="active",
        expiry_date__gt=timezone.now(),
        plan__product__in=["flipbook", "all"],
    )


def prefer_flipbook_plan(rows):
    """A Flipbook plan wins over an All plan."""
    fallback = None
    for row in rows:
        if row.plan.product == "flipbook":
            return row
        fallback = row
    return fallback


def has_active_user_plan(user) -> bool:
    """True when a paid Flipbook or All plan is still active. The welcome plan does not count."""
    return active_flipbook_plans(user).filter(plan__price__gt=0).exists()


def flipbook_plan_type(user) -> str:
    """Studio or lab from a paid Flipbook or All plan. Welcome credits stay on the user tier."""
    row = prefer_flipbook_plan(active_flipbook_plans(user).filter(plan__price__gt=0))
    if row is not None:
        return row.plan.plan_type
    return user.plan or "studio"


def resolve_active_until(user):
    """
    Welcome credits and accounts with no paid plan: flipbooks expire after 30 days.
    A paid Flipbook or All plan has no fixed expiry (active_until stays null).
    """
    if has_active_user_plan(user):
        return None
    return timezone.now() + timedelta(days=FREE_FLIPBOOK_LIFETIME_DAYS)


def flipbook_plan_to_spend(user):
    """
    Active Flipbook plan with credits left, otherwise an active All plan.
    """
    fallback = None
    for row in active_flipbook_plans(user):
        remaining = int(row.credits_total or 0) - int(row.credits_used or 0)
        if remaining < 1:
            continue
        if row.plan.product == "flipbook":
            return row
        fallback = row
    return fallback


def validate_user_credits(user) -> None:
    """Raise ValidationError if the user cannot spend 1 credit on a flipbook."""
    from rd_flip_be.models import UserPlan

    if flipbook_plan_to_spend(user) is not None:
        return

    now = timezone.now()
    covering = UserPlan.objects.filter(
        user=user,
        plan__product__in=["flipbook", "all"],
    )
    if covering.filter(status="active", expiry_date__gt=now).exists():
        raise serializers.ValidationError(
            "You do not have enough credits to create a flipbook."
        )
    if covering.exists():
        raise serializers.ValidationError(
            "Your plan has expired. Please renew to create a flipbook."
        )
    raise serializers.ValidationError(
        "You need a flipbook plan to create a flipbook."
    )


def deduct_user_credit(user, flipbook=None) -> None:
    plan_row = flipbook_plan_to_spend(user)
    if plan_row is None:
        raise serializers.ValidationError(
            "You do not have enough credits to create a flipbook."
        )

    plan_row.credits_used = int(plan_row.credits_used or 0) + 1
    plan_row.updated_by = user.user_id
    plan_row.save(update_fields=["credits_used", "updated_by", "updated_at"])
    create_credit_transaction(
        user=user,
        credit_type="usage",
        credits=-1,
        flipbook=flipbook,
        user_plan=plan_row,
        description=(
            f"Credit used to create flipbook {flipbook.flip_id}"
            if flipbook is not None
            else "Credit used to create flipbook"
        ),
        created_by=user.user_id,
    )
