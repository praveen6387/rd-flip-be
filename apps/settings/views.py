from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from rd_flip_be.models import Setting
from rd_flip_be.responses import api_success

LEGAL_SETTING_KEYS = ("privacy_policy", "terms_and_conditions", "refund")


class LegalSettingsView(APIView):
    """Public settings: privacy_policy + terms_and_conditions in one response."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        rows = Setting.objects.filter(key__in=LEGAL_SETTING_KEYS).only("key", "value")
        by_key = {row.key: row.value for row in rows}

        return api_success(
            message="Settings fetched",
            data={
                "privacy_policy": by_key.get("privacy_policy"),
                "terms_and_conditions": by_key.get("terms_and_conditions"),
                "refund": by_key.get("refund"),
            },
        )
