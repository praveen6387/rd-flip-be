from django.utils import timezone

from rd_flip_be.credits import create_credit_transaction
from rd_flip_be.models import CreditTransaction


def allocate_purchase_credits(*, user, plan, order, user_plan) -> None:
    """
    Allocate plan credits to the user after a successful paid order.

    Safe to call only once per order (skips if a purchase CreditTransaction
    already exists for this order).
    """
    if CreditTransaction.objects.filter(order=order, credit_type="purchase").exists():
        return

    purchased = int(plan.credit or 0)
    if purchased <= 0:
        return

    today = timezone.localdate()
    old_left = int(user.left_credit or 0)
    old_expire = user.credit_expire_date
    new_expire_date = timezone.localtime(user_plan.expiry_date).date()

    credits_are_expired = (
        old_expire is not None and old_expire < today and old_left > 0
    )

    if credits_are_expired:
        create_credit_transaction(
            user=user,
            credit_type="expiry",
            credits=-old_left,
            order=order,
            expiry_date=old_expire,
            description=f"Expired {old_left} unused credit(s) before plan purchase",
            created_by=user.user_id,
        )
        user.expired_credit = int(user.expired_credit or 0) + old_left
        user.left_credit = purchased
    else:
        user.left_credit = old_left + purchased

    user.total_credit = int(user.total_credit or 0) + purchased
    user.credit_expire_date = new_expire_date
    user.plan = plan.plan_type
    user.updated_by = user.user_id
    user.save(
        update_fields=[
            "total_credit",
            "left_credit",
            "expired_credit",
            "credit_expire_date",
            "plan",
            "updated_by",
            "updated_at",
        ]
    )

    create_credit_transaction(
        user=user,
        credit_type="purchase",
        credits=purchased,
        order=order,
        expiry_date=user_plan.expiry_date,
        description=f"Purchased {purchased} credit(s) from plan {plan.name}",
        created_by=user.user_id,
    )
