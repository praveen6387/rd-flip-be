import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rd_flip_be", "0024_alter_flipbook_studio_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="product",
            field=models.CharField(
                choices=[
                    ("flipbook", "Flipbook"),
                    ("photo_selection", "Photo Selection"),
                    ("all", "All"),
                ],
                default="flipbook",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="userplan",
            name="credits_total",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="userplan",
            name="credits_used",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="credittransaction",
            name="user_plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="credit_transactions",
                to="rd_flip_be.userplan",
            ),
        ),
    ]
