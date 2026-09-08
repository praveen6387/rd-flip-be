from django.urls import path

from apps.payments.views import VerifyPaymentView

urlpatterns = [
    path("verify/", VerifyPaymentView.as_view(), name="payment-verify"),
]
