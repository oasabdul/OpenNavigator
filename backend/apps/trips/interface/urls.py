from __future__ import annotations

from django.urls import path

from apps.trips.interface.views import ConfigView, HealthView, HeatmapView, PlanTripView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("config/", ConfigView.as_view(), name="config"),
    path("trips/plan/", PlanTripView.as_view(), name="plan-trip"),
    path(
        "trips/<uuid:plan_id>/heatmap/",
        HeatmapView.as_view(),
        name="trip-heatmap",
    ),
]
