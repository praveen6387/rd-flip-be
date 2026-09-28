from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rd_flip_be", "0019_song_category_blank"),
    ]

    operations = [
        migrations.AlterField(
            model_name="song",
            name="audio_url",
            field=models.CharField(max_length=2048),
        ),
    ]
