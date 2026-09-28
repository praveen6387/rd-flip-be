from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.songs.serializers import CreateSongSerializer, SongSerializer
from rd_flip_be.models import Song
from rd_flip_be.responses import api_success


class SongListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        query = str(request.query_params.get("q") or "").strip()
        songs = Song.objects.filter(is_active=True)
        if query:
            songs = songs.filter(name__icontains=query)
        songs = songs.order_by("name")

        return api_success(
            message="Songs fetched",
            data={"songs": SongSerializer(songs, many=True).data},
        )


class SongCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = CreateSongSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        song = serializer.save()
        return api_success(
            message="Song added",
            data={"song": SongSerializer(song).data},
            http_status=status.HTTP_201_CREATED,
        )
