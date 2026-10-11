from datetime import datetime, time, timedelta

from django.db import migrations
from django.utils import timezone


def create_welcome_plan_and_move_signup_credits(apps, schema_editor):
    Plan = apps.get_model("rd_flip_be", "Plan")
    User = apps.get_model("rd_flip_be", "User")
    UserPlan = apps.get_model("rd_flip_be", "UserPlan")
    CreditTransaction = apps.get_model("rd_flip_be", "CreditTransaction")

    plan, _created = Plan.objects.get_or_create(
        name="Welcome",
        plan_type="studio",
        product="flipbook",
        defaults={
            "price": 0,
            "credit": 5,
            "validity_days": 7,
            "features": [],
            "is_active": False,
        },
    )

    today = timezone.localdate()
    for user in User.objects.filter(user_plans__isnull=True).distinct():
        used = int(user.used_credit or 0)
        left = int(user.left_credit or 0)
        total = int(user.total_credit or 0)
        if total == 0 and used == 0 and left == 0 and user.credit_expire_date is None:
            continue

        credits_total = max(total, used + left)
        credits_used = min(used, credits_total)
        expire = user.credit_expire_date
        if expire is not None:
            expiry = timezone.make_aware(datetime.combine(expire, time(23, 59, 59)))
            status = "active" if expire >= today else "expired"
        else:
            start = user.created_at or timezone.now()
            expiry = start + timedelta(days=7)
            status = "expired" if expiry <= timezone.now() else "active"

        user_plan = UserPlan.objects.create(
            user_id=user.id,
            plan_id=plan.id,
            start_date=user.created_at or timezone.now(),
            expiry_date=expiry,
            credits_total=credits_total,
            credits_used=credits_used,
            status=status,
            created_by=user.user_id,
            updated_by=user.user_id,
        )
        CreditTransaction.objects.filter(
            user_id=user.id,
            credit_type="free",
            user_plan__isnull=True,
        ).update(user_plan_id=user_plan.id)
        User.objects.filter(pk=user.pk).update(
            total_credit=0,
            used_credit=0,
            left_credit=0,
            expired_credit=0,
            credit_expire_date=None,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("rd_flip_be", "0025_plan_product_and_userplan_credits"),
    ]

    operations = [
        migrations.RunPython(
            create_welcome_plan_and_move_signup_credits,
            migrations.RunPython.noop,
        ),
    ]
