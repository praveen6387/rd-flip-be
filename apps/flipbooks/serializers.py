from django.db import transaction
from rest_framework import serializers

from apps.auth.helpers import normalize_indian_phone
from apps.flipbooks.helpers import first_non_empty, unique_flip_id
from rd_flip_be.models import Flipbook, FlipbookPage


class FlipbookImageSerializer(serializers.Serializer):
    page_number = serializers.IntegerField(min_value=1)
    image_url = serializers.URLField(max_length=2048)
    cover_type = serializers.ChoiceField(choices=FlipbookPage.COVER_TYPE_CHOICES)


class FlipbookPageResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlipbookPage
        fields = (
            "id",
            "page_number",
            "image_url",
            "cover_type",
            "created_at",
        )


class FlipbookResponseSerializer(serializers.ModelSerializer):
    pages = FlipbookPageResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Flipbook
        fields = (
            "id",
            "flip_id",
            "title",
            "description",
            "date",
            "studio_name",
            "whatsapp_number",
            "instagram_url",
            "facebook_url",
            "total_pages",
            "pages",
            "created_at",
            "updated_at",
        )


class FlipbookListSerializer(serializers.ModelSerializer):
    thumbnail = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)

    class Meta:
        model = Flipbook
        fields = (
            "id",
            "flip_id",
            "title",
            "description",
            "date",
            "studio_name",
            "whatsapp_number",
            "instagram_url",
            "facebook_url",
            "total_pages",
            "thumbnail",
            "created_at",
            "updated_at",
        )


class CreateFlipbookSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    date = serializers.DateField()
    images = FlipbookImageSerializer(many=True)
    studio_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    whatsapp_number = serializers.CharField(
        required=False, allow_blank=True, max_length=20
    )
    instagram_url = serializers.URLField(required=False, allow_blank=True)
    facebook_url = serializers.URLField(required=False, allow_blank=True)

    def validate_images(self, images):
        if not images:
            raise serializers.ValidationError("Provide at least one image.")
        page_numbers = [item["page_number"] for item in images]
        if len(page_numbers) != len(set(page_numbers)):
            raise serializers.ValidationError("Duplicate page_number in images.")
        return images

    def validate_whatsapp_number(self, value):
        number = (value or "").strip()
        if not number:
            return ""
        return normalize_indian_phone(number)

    def _branding_from_user(self, user) -> dict:
        return {
            "studio_name": (user.studio_name or "").strip(),
            "whatsapp_number": (user.whatsapp_number or "").strip(),
            "instagram_url": (user.instagram_url or "").strip(),
            "facebook_url": (user.facebook_url or "").strip(),
        }

    def _resolve_branding(self, user, payload: dict) -> dict:
        profile = self._branding_from_user(user)

        if user.plan == "lab":
            branding = {
                "studio_name": first_non_empty(
                    payload.get("studio_name"), profile["studio_name"]
                ),
                "whatsapp_number": first_non_empty(
                    payload.get("whatsapp_number"), profile["whatsapp_number"]
                ),
                "instagram_url": first_non_empty(
                    payload.get("instagram_url"), profile["instagram_url"]
                ),
                "facebook_url": first_non_empty(
                    payload.get("facebook_url"), profile["facebook_url"]
                ),
            }
        else:
            branding = profile

        if not branding["studio_name"]:
            raise serializers.ValidationError(
                {"studio_name": "Studio name is required. Add it on your profile."}
            )
        if not branding["whatsapp_number"]:
            raise serializers.ValidationError(
                {
                    "whatsapp_number": (
                        "WhatsApp number is required. Add it on your profile."
                    )
                }
            )
        return branding

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        images = sorted(validated_data["images"], key=lambda item: item["page_number"])
        branding = self._resolve_branding(user, validated_data)

        with transaction.atomic():
            flipbook = Flipbook.objects.create(
                user=user,
                title=validated_data["title"].strip(),
                description=(validated_data.get("description") or "").strip(),
                date=validated_data["date"],
                studio_name=branding["studio_name"],
                whatsapp_number=branding["whatsapp_number"],
                instagram_url=branding["instagram_url"],
                facebook_url=branding["facebook_url"],
                total_pages=len(images),
                flip_id=unique_flip_id(),
                created_by=user.user_id,
                updated_by=user.user_id,
            )
            FlipbookPage.objects.bulk_create(
                [
                    FlipbookPage(
                        flipbook=flipbook,
                        page_number=item["page_number"],
                        image_url=item["image_url"],
                        cover_type=item["cover_type"],
                        created_by=user.user_id,
                        updated_by=user.user_id,
                    )
                    for item in images
                ]
            )

        return flipbook
