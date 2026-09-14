from rest_framework import serializers

from apps.auth.helpers import normalize_indian_phone
from rd_flip_be.models import ContactUs


class CreateContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = ("name", "email", "phone_number", "message")

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Name is required.")
        if len(name) < 2:
            raise serializers.ValidationError("Enter a valid name.")
        return name

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if not email:
            raise serializers.ValidationError("Email is required.")
        return email

    def validate_phone_number(self, value):
        return normalize_indian_phone(value)

    def validate_message(self, value):
        message = (value or "").strip()
        if not message:
            raise serializers.ValidationError("Message is required.")
        if len(message) < 5:
            raise serializers.ValidationError("Message is too short.")
        return message


class ContactUsResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = (
            "id",
            "name",
            "email",
            "phone_number",
            "message",
            "created_at",
        )
