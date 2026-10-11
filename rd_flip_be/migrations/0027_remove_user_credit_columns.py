from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rd_flip_be", "0026_welcome_plan"),
    ]

    operations = [
        migrations.RemoveField(model_name="user", name="total_credit"),
        migrations.RemoveField(model_name="user", name="used_credit"),
        migrations.RemoveField(model_name="user", name="left_credit"),
        migrations.RemoveField(model_name="user", name="expired_credit"),
        migrations.RemoveField(model_name="user", name="credit_expire_date"),
    ]
