from django.urls import path

from apps.settings.views import LegalSettingsView

# /api/settings/
urlpatterns = [
    path("legal/", LegalSettingsView.as_view(), name="settings-legal"),
]
