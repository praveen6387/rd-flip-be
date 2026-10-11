from rd_flip_be.credits import create_credit_transaction
from rd_flip_be.models import CreditTransaction, UserPlan


def products_replaced_by(product):
    """An All purchase replaces both products. Any other purchase replaces only itself."""
    if product == "all":
        return ["flipbook", "photo_selection", "all"]
    return [product]


def close_replaced_plans(user, product, now):
    """Expire the active plan rows this purchase replaces. Their unused credits are not carried over."""
    UserPlan.objects.filter(
        user=user,
        status="active",
        plan__product__in=products_replaced_by(product),
    ).update(
        status="expired",
        updated_at=now,
        updated_by=user.user_id,
    )


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

    user_plan.credits_total = purchased
    user_plan.credits_used = 0
    user_plan.updated_by = user.user_id
    user_plan.save(
        update_fields=["credits_total", "credits_used", "updated_by", "updated_at"]
    )

    if plan.product in ("flipbook", "all") and user.plan != plan.plan_type:
        user.plan = plan.plan_type
        user.updated_by = user.user_id
        user.save(update_fields=["plan", "updated_by", "updated_at"])

    create_credit_transaction(
        user=user,
        credit_type="purchase",
        credits=purchased,
        order=order,
        user_plan=user_plan,
        expiry_date=user_plan.expiry_date,
        description=f"Purchased {purchased} credit(s) from plan {plan.name}",
        created_by=user.user_id,
    )
