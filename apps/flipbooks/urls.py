from django.urls import path

from apps.flipbooks.views import (
    FlipbookCreateView,
    FlipbookDetailView,
    FlipbookListView,
    PublicFlipbookView,
)

# api/flipbooks/

urlpatterns = [
    path("", FlipbookListView.as_view(), name="flipbook-list"),
    path("create/", FlipbookCreateView.as_view(), name="flipbook-create"),
    path("<int:id>/", FlipbookDetailView.as_view(), name="flipbook-detail"),  # use for delete
    path("<str:flip_id>/", PublicFlipbookView.as_view(), name="flipbook-public"),
]
