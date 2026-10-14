from django.urls import path
from .views import AlbumsView, AlbumView, PhotoView, PublicAlbumView, SelectionCodeView
urlpatterns = [
    path("", AlbumsView.as_view()),
    path("access/", SelectionCodeView.as_view()),
    path("public/<uuid:token>/", PublicAlbumView.as_view()),
    path("<uuid:album_id>/", AlbumView.as_view()),
    path("<uuid:album_id>/photos/<uuid:photo_id>/", PhotoView.as_view()),
]
