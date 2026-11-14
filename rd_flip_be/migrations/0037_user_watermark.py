from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0036_selectionphoto_relative_path_unique")]
    operations = [
        migrations.AddField(model_name="user", name="watermark_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="user", name="watermark_text", field=models.CharField(blank=True, default="", max_length=120)),
        migrations.AddField(model_name="user", name="watermark_position", field=models.CharField(blank=True, default="bottom-right", max_length=20)),
        migrations.AddField(model_name="user", name="watermark_opacity", field=models.FloatField(default=0.45)),
    ]
