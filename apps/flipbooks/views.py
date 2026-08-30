from django.db.models import OuterRef, Prefetch, Subquery
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.flipbooks.serializers import (
    CreateFlipbookSerializer,
    FlipbookListSerializer,
    FlipbookResponseSerializer,
    PublicFlipbookSerializer,
)
from rd_flip_be.models import Flipbook, FlipbookPage
from rd_flip_be.responses import api_fail, api_success


class FlipbookListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        thumbnail = (
            FlipbookPage.objects.filter(flipbook_id=OuterRef("pk"))
            .order_by("page_number")
            .values("image_url")[:1]
        )
        flipbooks = (
            Flipbook.objects.filter(user=request.user)
            .annotate(thumbnail=Subquery(thumbnail))
            .order_by("-created_at")
        )
        return api_success(
            message="Flipbooks fetched",
            data={"flipbooks": FlipbookListSerializer(flipbooks, many=True).data},
        )


class FlipbookCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = CreateFlipbookSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        flipbook = serializer.save()
        flipbook = Flipbook.objects.prefetch_related("pages").get(pk=flipbook.pk)
        return api_success(
            message="Flipbook created",
            data={"flipbook": FlipbookResponseSerializer(flipbook).data},
            http_status=status.HTTP_201_CREATED,
        )


class PublicFlipbookView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request, flip_id: str):
        flip_id = (flip_id or "").strip()
        if len(flip_id) != 10:
            return api_fail(
                message="Flipbook not found.",
                details="Flipbook not found.",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        pages_qs = FlipbookPage.objects.order_by("page_number").only(
            "id",
            "flipbook_id",
            "page_number",
            "image_url",
            "cover_type",
        )
        flipbook = (
            Flipbook.objects.filter(flip_id=flip_id)
            .only(
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
            )
            .prefetch_related(Prefetch("pages", queryset=pages_qs))
            .first()
        )
        if flipbook is None:
            return api_fail(
                message="Flipbook not found.",
                details="Flipbook not found.",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        return api_success(
            message="Flipbook fetched",
            data={"flipbook": PublicFlipbookSerializer(flipbook).data},
        )
