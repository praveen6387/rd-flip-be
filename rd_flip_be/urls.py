from django.contrib import admin
from django.urls import include, path

# url entry point
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.auth.urls")),
    path("api/flipbooks/", include("apps.flipbooks.urls")),
    path("api/plans/", include("apps.plans.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/settings/", include("apps.settings.urls")),
    path("api/contact/", include("apps.contact.urls")),
]
