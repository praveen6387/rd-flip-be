from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rd_flip_be", "0017_song"),
    ]

    operations = [
        migrations.AddField(
            model_name="flipbook",
            name="song_id",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
