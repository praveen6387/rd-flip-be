from django.urls import path

from apps.auth.views import (
    ChangePasswordView,
    HealthCheckView,
    LoginView,
    MeView,
    RefreshTokenView,
    SignupView,
)

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="auth-health"),
    path("signup/", SignupView.as_view(), name="auth-signup"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
]
