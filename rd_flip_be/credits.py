from datetime import datetime, time

from django.utils import timezone

from rd_flip_be.models import CreditTransaction


def _as_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value)
        return value
    return timezone.make_aware(datetime.combine(value, time.min))


def create_credit_transaction(
    *,
    user,
    credit_type: str,
    credits: int,
    description: str = "",
    order=None,
    flipbook=None,
    expiry_date=None,
    created_by=None,
) -> CreditTransaction:
    """
    Create a CreditTransaction row for any credit add/deduct.
    Use positive credits for add, negative for deduct.
    """
    if created_by is None and getattr(user, "user_id", None):
        created_by = user.user_id

    return CreditTransaction.objects.create(
        user=user,
        credit_type=credit_type,
        credits=credits,
        order=order,
        flipbook=flipbook,
        expiry_date=_as_datetime(expiry_date),
        description=(description or "").strip(),
        created_by=created_by,
    )
