from django.db.models import OuterRef, Subquery
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.flipbooks.serializers import (
    CreateFlipbookSerializer,
    FlipbookListSerializer,
    FlipbookResponseSerializer,
)
from rd_flip_be.models import Flipbook, FlipbookPage
from rd_flip_be.responses import api_success


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
