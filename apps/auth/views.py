from django.db.models import Prefetch, Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth.serializers import (
    AdminUserListSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    SignupResponseSerializer,
    SignupSerializer,
    UpdateSocialLinksSerializer,
    UserProfileSerializer,
)
from django.contrib.auth import get_user_model
from rd_flip_be.models import CreditTransaction, Order, UserPlan
from rd_flip_be.permissions import IsAdminRole
from rd_flip_be.responses import api_success

User = get_user_model()


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


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return api_success(
            message="Profile fetched",
            data={"user": UserProfileSerializer(request.user).data},
        )

    def put(self, request):
        serializer = UpdateSocialLinksSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return api_success(
            message="Profile updated",
            data={"user": UserProfileSerializer(user).data},
        )


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_success(message="Password updated")


class ForgotPasswordView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_success(message="Password reset link sent")


class ResetPasswordView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_success(message="Password updated")


class AdminUserListView(APIView):
    permission_classes = (IsAuthenticated, IsAdminRole)

    def get(self, request):
        query = str(request.query_params.get("q") or "").strip()
        users = User.objects.prefetch_related(
            Prefetch(
                "credit_transactions",
                queryset=CreditTransaction.objects.select_related(
                    "order", "flipbook"
                ).order_by("-created_at"),
            ),
            Prefetch(
                "orders",
                queryset=Order.objects.select_related("plan")
                .prefetch_related("payment_transactions")
                .order_by("-created_at"),
            ),
            Prefetch(
                "user_plans",
                queryset=UserPlan.objects.select_related("plan").order_by(
                    "-created_at"
                ),
            ),
        ).order_by("-id")
        if query:
            users = users.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
                | Q(studio_name__icontains=query)
            )

        return api_success(
            message="Users fetched",
            data={"users": AdminUserListSerializer(users, many=True).data},
        )
