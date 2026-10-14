from django.db import migrations, models
import rd_flip_be.models


def fill_codes(apps, schema_editor):
    Album = apps.get_model("rd_flip_be", "PhotoSelection")
    rows = Album.objects.using(schema_editor.connection.alias)
    used = set(rows.exclude(access_code=None).values_list("access_code", flat=True))
    for album in rows.filter(access_code=None).iterator():
        while True:
            code = rd_flip_be.models.generate_selection_code()
            if code not in used:
                used.add(code)
                break
        album.access_code = code
        album.save(using=schema_editor.connection.alias, update_fields=["access_code"])


class Migration(migrations.Migration):
    dependencies = [("rd_flip_be", "0031_selectionphoto_original_relative_path")]
    operations = [
        migrations.AddField(model_name="photoselection", name="access_code", field=models.CharField(max_length=6, unique=True, null=True, editable=False)),
        migrations.RunPython(fill_codes, migrations.RunPython.noop),
        migrations.AlterField(model_name="photoselection", name="access_code", field=models.CharField(max_length=6, unique=True, editable=False, default=rd_flip_be.models.generate_selection_code)),
    ]
