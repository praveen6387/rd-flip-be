from rest_framework import serializers

from rd_flip_be.models import Plan


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "name",
            "plan_type",
            "price",
            "credit",
            "validity_days",
            "is_active",
            "created_at",
            "updated_at",
        )
