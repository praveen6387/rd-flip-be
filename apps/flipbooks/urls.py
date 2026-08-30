from django.urls import path

from apps.flipbooks.views import FlipbookCreateView

urlpatterns = [
    path("", FlipbookCreateView.as_view(), name="flipbook-create"),
]
