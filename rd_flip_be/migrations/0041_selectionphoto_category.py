from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0040_selectionphoto_rotation")]
    operations = [
        migrations.AddField(model_name="selectionphoto", name="category", field=models.CharField(blank=True, default="", max_length=100)),
    ]
