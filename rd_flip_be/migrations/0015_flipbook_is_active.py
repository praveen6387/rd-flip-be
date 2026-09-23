from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rd_flip_be", "0014_contactus"),
    ]

    operations = [
        migrations.AddField(
            model_name="flipbook",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
