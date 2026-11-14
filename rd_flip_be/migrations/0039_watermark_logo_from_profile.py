from django.db import migrations, models


def use_profile_logo(apps, schema_editor):
    User = apps.get_model("rd_flip_be", "User")
    User.objects.exclude(watermark_logo_url="").update(watermark_include_logo=True)


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0038_user_watermark_logo")]
    operations = [
        migrations.AlterField(model_name="user", name="watermark_include_logo", field=models.BooleanField(default=True)),
        migrations.RunPython(use_profile_logo, migrations.RunPython.noop),
    ]
