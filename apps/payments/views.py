from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.orders.serializers import OrderResponseSerializer
from apps.payments.serializers import VerifyPaymentSerializer
from rd_flip_be.responses import api_success


class VerifyPaymentView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = VerifyPaymentSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        already_paid = serializer.validated_data.get("already_paid", False)
        return api_success(
            message=(
                "Payment already verified"
                if already_paid
                else "Payment verified"
            ),
            data={
                "order": OrderResponseSerializer(order).data,
                "razorpay_payment_id": request.data.get("razorpay_payment_id"),
            },
        )
