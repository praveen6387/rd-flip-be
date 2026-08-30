from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.flipbooks.serializers import (
    CreateFlipbookSerializer,
    FlipbookResponseSerializer,
)
from rd_flip_be.models import Flipbook
from rd_flip_be.responses import api_success


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
