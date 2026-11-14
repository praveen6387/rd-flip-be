from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0032_photo_selection_access_code")]
    operations = [
        migrations.AddField(model_name="photoselection", name="selection_mode", field=models.CharField(default="UNLIMITED", max_length=20)),
        migrations.AddField(model_name="photoselection", name="required_photos", field=models.PositiveIntegerField(default=100)),
        migrations.AddField(model_name="photoselection", name="included_photos", field=models.PositiveIntegerField(default=100)),
        migrations.AddField(model_name="photoselection", name="allow_extra_photos", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="photoselection", name="strict_limit", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="photoselection", name="max_selection_limit", field=models.PositiveIntegerField(default=100)),
        migrations.AddField(model_name="photoselection", name="photos_per_sheet", field=models.PositiveIntegerField(default=4)),
        migrations.AddField(model_name="photoselection", name="included_sheets", field=models.PositiveIntegerField(default=25)),
        migrations.AddField(model_name="photoselection", name="enable_extra_photo_pricing", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="photoselection", name="extra_photo_price", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="photoselection", name="enable_extra_sheet_pricing", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="photoselection", name="extra_sheet_price", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="photoselection", name="rules_configured", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="photoselection", name="confirmed_by_name", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="photoselection", name="confirmation_notes", field=models.TextField(blank=True)),
        migrations.AddField(model_name="photoselection", name="confirmed_selected_count", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="photoselection", name="extra_photos_count", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="photoselection", name="extra_sheets_count", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="photoselection", name="estimated_sheets", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="photoselection", name="extra_photo_charge", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="photoselection", name="extra_sheet_charge", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="photoselection", name="total_extra_charge", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="selectionphoto", name="rating", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="selectionphoto", name="cover_type", field=models.CharField(blank=True, max_length=5)),
        migrations.AddField(model_name="selectionphoto", name="notes", field=models.TextField(blank=True)),
    ]
