from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rd_flip_be", "0018_flipbook_song_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="song",
            name="category",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
