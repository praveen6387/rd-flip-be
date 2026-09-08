from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from apps.orders.helpers import unique_order_name
from apps.payments.services.razorpay_service import create_razorpay_order
from rd_flip_be.models import Order, Plan


class CreateOrderSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField(min_value=1)

    def validate_plan_id(self, value):
        plan = Plan.objects.filter(id=value, is_active=True).first()
        if plan is None:
            raise serializers.ValidationError("Invalid plan.")
        self.context["plan"] = plan
        return value

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        plan = self.context["plan"]

        with transaction.atomic():
            order = Order.objects.create(
                order_name=unique_order_name(),
                user=user,
                plan=plan,
                amount=plan.price,
                payment_status="pending",
                created_by=user.user_id,
                updated_by=user.user_id,
            )

            try:
                razorpay_order = create_razorpay_order(order)
            except Exception:
                raise serializers.ValidationError(
                    "Unable to create payment order. Please try again."
                )

            order.gateway_order_id = razorpay_order["id"]
            order.save(update_fields=["gateway_order_id", "updated_at"])
            self.context["razorpay_order"] = razorpay_order

        return order


class OrderResponseSerializer(serializers.ModelSerializer):
    plan_id = serializers.IntegerField(source="plan.id", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_type = serializers.CharField(source="plan.plan_type", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_name",
            "plan_id",
            "plan_name",
            "plan_type",
            "amount",
            "payment_status",
            "gateway_order_id",
            "created_at",
        )


def build_order_create_response(order, razorpay_order: dict | None = None) -> dict:
    """Order payload + Razorpay fields the FE needs to open checkout."""
    razorpay_order = razorpay_order or {}
    return {
        "order": OrderResponseSerializer(order).data,
        "razorpay": {
            "key_id": settings.RAZORPAY_KEY_ID,
            "order_id": order.gateway_order_id,
            "amount": razorpay_order.get("amount", int(order.amount * 100)),
            "currency": razorpay_order.get("currency", "INR"),
        },
    }
