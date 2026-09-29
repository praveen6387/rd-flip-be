from django.urls import path

from apps.orders.views import AdminOrderListView, OrderCreateView

urlpatterns = [
    path("", AdminOrderListView.as_view(), name="order-list"),
    path("create/", OrderCreateView.as_view(), name="order-create"),
]
