from django.urls import path

from apps.flipbooks.views import (
    FlipbookCreateView,
    FlipbookDetailView,
    FlipbookLikeView,
    FlipbookListView,
    FlipbookRecordView,
    PublicFlipbookView,
)

# api/flipbooks/

urlpatterns = [
    path("", FlipbookListView.as_view(), name="flipbook-list"),
    path("create/", FlipbookCreateView.as_view(), name="flipbook-create"),
    path("<int:id>/", FlipbookDetailView.as_view(), name="flipbook-detail"),  # use for delete
    path("<str:flip_id>/view/", FlipbookRecordView.as_view(), name="flipbook-record-view"),
    path("<str:flip_id>/like/", FlipbookLikeView.as_view(), name="flipbook-like"),
    path("<str:flip_id>/", PublicFlipbookView.as_view(), name="flipbook-public"),
]
