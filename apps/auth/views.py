from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth.serializers import (
    LoginSerializer,
    SignupResponseSerializer,
    SignupSerializer,
)


class HealthCheckView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"status": "ok"})


class SignupView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Signup successful",
                "user": SignupResponseSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Login successful",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                "user": SignupResponseSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class RefreshTokenView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = {"access": serializer.validated_data["access"]}
        if "refresh" in serializer.validated_data:
            tokens["refresh"] = serializer.validated_data["refresh"]

        return Response(
            {
                "message": "Token refreshed",
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )
