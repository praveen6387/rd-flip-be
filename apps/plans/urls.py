from django.urls import path

from apps.plans.views import PlanListView

# /api/plans/
urlpatterns = [
    path("", PlanListView.as_view(), name="plan-list"),
]
