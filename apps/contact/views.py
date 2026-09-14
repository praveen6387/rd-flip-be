from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.contact.serializers import (
    ContactUsResponseSerializer,
    CreateContactUsSerializer,
)
from rd_flip_be.responses import api_success


class ContactUsCreateView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = CreateContactUsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        return api_success(
            message="Message sent",
            data={"contact": ContactUsResponseSerializer(contact).data},
            http_status=status.HTTP_201_CREATED,
        )
