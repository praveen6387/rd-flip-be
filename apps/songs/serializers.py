from rest_framework import serializers

from rd_flip_be.models import Song


class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = (
            "id",
            "name",
            "category",
            "description",
            "audio_url",
        )


class CreateSongSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    audio_url = serializers.CharField(max_length=2048)

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Song name is required.")
        return name

    def validate_audio_url(self, value):
        url = (value or "").strip()
        if not url:
            raise serializers.ValidationError("Song URL is required.")
        return url

    def create(self, validated_data):
        return Song.objects.create(
            name=validated_data["name"],
            category="",
            description="",
            audio_url=validated_data["audio_url"],
            is_active=True,
        )
