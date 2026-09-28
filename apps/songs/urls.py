from django.urls import path

from apps.songs.views import SongCreateView, SongListView

# /api/songs/
urlpatterns = [
    path("", SongListView.as_view(), name="song-list"),
    path("create/", SongCreateView.as_view(), name="song-create"),
]
