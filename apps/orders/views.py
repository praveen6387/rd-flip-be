from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.orders.serializers import (
    AdminOrderListSerializer,
    CreateOrderSerializer,
    build_order_create_response,
)
from rd_flip_be.models import Order
from rd_flip_be.permissions import IsAdminRole
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


class AdminOrderListView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request):
        query = str(request.query_params.get("q") or "").strip()
        orders = Order.objects.select_related("user", "plan").order_by("-created_at")
        if query:
            orders = orders.filter(
                Q(order_name__icontains=query)
                | Q(payment_status__icontains=query)
                | Q(plan__name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__phone__icontains=query)
            )

        return api_success(
            message="Orders fetched",
            data={"orders": AdminOrderListSerializer(orders, many=True).data},
        )
