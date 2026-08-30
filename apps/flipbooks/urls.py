from django.urls import path

from apps.flipbooks.views import FlipbookCreateView, FlipbookListView

urlpatterns = [
    path("", FlipbookListView.as_view(), name="flipbook-list"),
    path("create/", FlipbookCreateView.as_view(), name="flipbook-create"),
]
