from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0039_watermark_logo_from_profile")]
    operations = [
        migrations.AddField(model_name="selectionphoto", name="rotation", field=models.PositiveSmallIntegerField(default=0)),
    ]
