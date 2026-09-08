from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.orders.serializers import (
    CreateOrderSerializer,
    build_order_create_response,
)
from rd_flip_be.responses import api_success


class OrderCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = CreateOrderSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return api_success(
            message="Order created",
            data=build_order_create_response(
                order,
                razorpay_order=serializer.context.get("razorpay_order"),
            ),
            http_status=status.HTTP_201_CREATED,
        )
