from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0033_photo_selection_rules")]
    operations = [
        migrations.AddField(model_name="photoselection", name="wizard_step", field=models.PositiveSmallIntegerField(default=1)),
        migrations.AddField(model_name="photoselection", name="welcome_message", field=models.TextField(blank=True, default="")),
    ]
