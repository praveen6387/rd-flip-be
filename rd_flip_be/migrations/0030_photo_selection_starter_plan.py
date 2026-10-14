from decimal import Decimal

from django.db import migrations


def create_photo_selection_plan(apps, schema_editor):
    Plan = apps.get_model("rd_flip_be", "Plan")
    Plan.objects.using(schema_editor.connection.alias).get_or_create(
        name="Photo Selection Starter",
        plan_type="studio",
        product="photo_selection",
        defaults={
            "price": Decimal("1.00"),
            "credit": 30,
            "validity_days": 30,
            "features": [
                "30 photo selection folders",
                "Credits valid for 30 days",
                "Private client selection links",
                "Export selected original photos",
            ],
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("rd_flip_be", "0029_photoselection_selectionphoto_and_more"),
    ]

    operations = [
        migrations.RunPython(create_photo_selection_plan, migrations.RunPython.noop),
    ]
