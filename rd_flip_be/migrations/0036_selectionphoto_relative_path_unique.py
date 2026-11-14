from django.db import migrations, models


def fill_blank_paths(apps, schema_editor):
    Photo = apps.get_model("rd_flip_be", "SelectionPhoto")
    for photo in Photo.objects.filter(original_relative_path=""):
        photo.original_relative_path = photo.original_name
        photo.save(update_fields=["original_relative_path"])


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0035_photoselection_client_details")]
    operations = [
        migrations.RunPython(fill_blank_paths, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name="selectionphoto", name="unique_selection_filename"),
        migrations.AddConstraint(model_name="selectionphoto", constraint=models.UniqueConstraint(fields=("album", "original_relative_path"), name="unique_selection_relative_path")),
    ]
