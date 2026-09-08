from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.payments.services.credit_allocation import allocate_purchase_credits
from apps.payments.services.razorpay_service import verify_razorpay_signature
from rd_flip_be.models import Order, PaymentTransaction, UserPlan

User = get_user_model()


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_payment_id = serializers.CharField(max_length=255)
    razorpay_order_id = serializers.CharField(max_length=255)
    razorpay_signature = serializers.CharField(max_length=512)

    def validate(self, attrs):
        request = self.context["request"]
        razorpay_order_id = attrs["razorpay_order_id"].strip()
        razorpay_payment_id = attrs["razorpay_payment_id"].strip()
        razorpay_signature = attrs["razorpay_signature"].strip()

        order = (
            Order.objects.select_related("plan").filter(gateway_order_id=razorpay_order_id, user=request.user).first()
        )
        if order is None:
            raise serializers.ValidationError("Order not found.")

        if order.payment_status == "paid":
            attrs["order"] = order
            attrs["already_paid"] = True
            attrs["razorpay_payment_id"] = razorpay_payment_id
            attrs["razorpay_signature"] = razorpay_signature
            return attrs

        if order.payment_status != "pending":
            raise serializers.ValidationError(f"Order cannot be verified (status: {order.payment_status}).")

        is_valid = verify_razorpay_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )
        if not is_valid:
            raise serializers.ValidationError("Payment signature verification failed.")

        if PaymentTransaction.objects.filter(gateway_payment_id=razorpay_payment_id).exists():
            raise serializers.ValidationError("Payment already recorded.")

        attrs["order"] = order
        attrs["already_paid"] = False
        attrs["razorpay_payment_id"] = razorpay_payment_id
        attrs["razorpay_signature"] = razorpay_signature
        attrs["razorpay_order_id"] = razorpay_order_id
        return attrs

    def save(self, **kwargs):
        order = self.validated_data["order"]
        if self.validated_data.get("already_paid"):
            return order

        request = self.context["request"]
        plan = order.plan
        razorpay_payment_id = self.validated_data["razorpay_payment_id"]
        razorpay_signature = self.validated_data["razorpay_signature"]
        razorpay_order_id = self.validated_data["razorpay_order_id"]

        now = timezone.now()
        expiry_date = now + timedelta(days=plan.validity_days)

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)

            PaymentTransaction.objects.create(
                order=order,
                gateway_payment_id=razorpay_payment_id,
                gateway_signature=razorpay_signature,
                amount=order.amount,
                payment_status="success",
                gateway_response={
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                },
            )

            # make the existing user plan as expired
            UserPlan.objects.filter(
                user=user,
                status="active",
            ).update(
                status="expired",
                updated_at=now,
                updated_by=user.user_id,
            )

            user_plan = UserPlan.objects.create(
                user=user,
                plan=plan,
                start_date=now,
                expiry_date=expiry_date,
                status="active",
                created_by=user.user_id,
                updated_by=user.user_id,
            )

            # allocate the credits to the user
            allocate_purchase_credits(
                user=user,
                plan=plan,
                order=order,
                user_plan=user_plan,
            )

            order.payment_status = "paid"
            order.user_plan = user_plan
            order.updated_by = user.user_id
            order.save(
                update_fields=[
                    "payment_status",
                    "user_plan",
                    "updated_by",
                    "updated_at",
                ]
            )

        return order
