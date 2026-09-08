from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.plans.serializers import PlanSerializer
from rd_flip_be.models import Plan
from rd_flip_be.responses import api_success


class PlanListView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        plans = Plan.objects.filter(is_active=True).order_by("price")
        return api_success(
            message="Plans fetched",
            data={"plans": PlanSerializer(plans, many=True).data},
        )
