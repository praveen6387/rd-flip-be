from django.db import migrations


def repair_unallocated_plan_credits(apps, schema_editor):
    """
    Purchases made before credits lived on UserPlan were stored as 0/0.
    Put the plan's own credit count on those rows, and count flipbook
    uses that happened during that plan.
    """
    UserPlan = apps.get_model("rd_flip_be", "UserPlan")
    CreditTransaction = apps.get_model("rd_flip_be", "CreditTransaction")

    for row in UserPlan.objects.select_related("plan").filter(credits_total=0):
        credit = int(row.plan.credit or 0)
        if credit <= 0:
            continue

        usage = CreditTransaction.objects.filter(
            user_id=row.user_id,
            credit_type="usage",
            created_at__gte=row.start_date,
            created_at__lte=row.expiry_date,
        )
        used = min(usage.count(), credit)
        UserPlan.objects.filter(pk=row.pk).update(
            credits_total=credit,
            credits_used=used,
        )
        usage.update(user_plan_id=row.id)

        purchase = (
            CreditTransaction.objects.filter(
                user_id=row.user_id,
                credit_type="purchase",
                user_plan__isnull=True,
                credits=credit,
                created_at__gte=row.start_date,
            )
            .order_by("created_at")
            .first()
        )
        if purchase is not None:
            purchase.user_plan_id = row.id
            purchase.save(update_fields=["user_plan"])

    for tx in CreditTransaction.objects.filter(credit_type="usage", user_plan__isnull=True):
        match = (
            UserPlan.objects.filter(
                user_id=tx.user_id,
                start_date__lte=tx.created_at,
                expiry_date__gte=tx.created_at,
                plan__product__in=["flipbook", "all"],
            )
            .order_by("-start_date")
            .first()
        )
        if match is not None:
            tx.user_plan_id = match.id
            tx.save(update_fields=["user_plan"])


class Migration(migrations.Migration):

    dependencies = [
        ("rd_flip_be", "0027_remove_user_credit_columns"),
    ]

    operations = [
        migrations.RunPython(repair_unallocated_plan_credits, migrations.RunPython.noop),
    ]
