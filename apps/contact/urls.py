from django.urls import path

from apps.contact.views import ContactUsCreateView

# /api/contact/
urlpatterns = [
    path("create/", ContactUsCreateView.as_view(), name="contact-create"),
]
