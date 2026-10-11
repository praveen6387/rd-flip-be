from datetime import timedelta

from django.utils import timezone

from rd_flip_be.credits import create_credit_transaction
from rd_flip_be.models import Plan, UserPlan

WELCOME_PLAN_NAME = "Welcome"
WELCOME_CREDITS = 5
WELCOME_DAYS = 7


def get_welcome_plan():
    """The free Flipbook plan. It is not listed for sale."""
    plan, _created = Plan.objects.get_or_create(
        name=WELCOME_PLAN_NAME,
        plan_type="studio",
        product="flipbook",
        defaults={
            "price": 0,
            "credit": WELCOME_CREDITS,
            "validity_days": WELCOME_DAYS,
            "features": [],
            "is_active": False,
        },
    )
    return plan


def grant_welcome_plan(user):
    """Give a new user their welcome credits on a plan row, not on the user account."""
    plan = get_welcome_plan()
    now = timezone.now()
    credits = int(plan.credit or WELCOME_CREDITS)
    expiry = now + timedelta(days=int(plan.validity_days or WELCOME_DAYS))
    user_plan = UserPlan.objects.create(
        user=user,
        plan=plan,
        start_date=now,
        expiry_date=expiry,
        credits_total=credits,
        credits_used=0,
        status="active",
        created_by=user.user_id,
        updated_by=user.user_id,
    )
    create_credit_transaction(
        user=user,
        credit_type="free",
        credits=credits,
        user_plan=user_plan,
        expiry_date=expiry,
        description="Welcome free credits on signup",
        created_by=user.user_id,
    )
    return user_plan
