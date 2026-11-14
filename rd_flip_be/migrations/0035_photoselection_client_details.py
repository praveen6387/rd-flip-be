from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0034_photoselection_wizard_step")]
    operations = [
        migrations.AddField(model_name="photoselection", name="whatsapp", field=models.CharField(blank=True, default="", max_length=30)),
        migrations.AddField(model_name="photoselection", name="client_email", field=models.CharField(blank=True, default="", max_length=255)),
        migrations.AddField(model_name="photoselection", name="event_date", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="photoselection", name="selection_deadline", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="photoselection", name="photographer_notes", field=models.TextField(blank=True, default="")),
    ]
