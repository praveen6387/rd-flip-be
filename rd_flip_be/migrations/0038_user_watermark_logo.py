from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0037_user_watermark")]
    operations = [
        migrations.AddField(model_name="user", name="watermark_include_logo", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="user", name="watermark_logo_url", field=models.CharField(blank=True, default="", max_length=500)),
    ]
