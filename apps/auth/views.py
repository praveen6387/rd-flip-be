from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth.serializers import (
    LoginSerializer,
    SignupResponseSerializer,
    SignupSerializer,
)
from rd_flip_be.responses import api_success


def _tokens_for_user(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class HealthCheckView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return api_success(message="OK", data={"status": "ok"})


class SignupView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return api_success(
            message="Signup successful",
            data={
                "tokens": _tokens_for_user(user),
                "user": SignupResponseSerializer(user).data,
            },
            http_status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return api_success(
            message="Login successful",
            data={
                "tokens": _tokens_for_user(user),
                "user": SignupResponseSerializer(user).data,
            },
        )


class RefreshTokenView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = {"access": serializer.validated_data["access"]}
        if "refresh" in serializer.validated_data:
            tokens["refresh"] = serializer.validated_data["refresh"]

        return api_success(message="Token refreshed", data={"tokens": tokens})
