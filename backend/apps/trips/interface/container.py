from __future__ import annotations

from django.conf import settings

from apps.trips.application.heatmap import HeatmapUseCase
from apps.trips.application.models import HeatmapConfig, PlanTripConfig
from apps.trips.application.plan_trip import PlanTripUseCase
from apps.trips.infrastructure.cache import DjangoFrameCache
from apps.trips.infrastructure.clock import SystemClock
from apps.trips.infrastructure.geocoding import NominatimGeocoder
from apps.trips.infrastructure.repository import DjangoPlanRepository
from apps.trips.infrastructure.routing import OsrmRouter
from apps.trips.infrastructure.weather import OpenMeteoWeather


def build_plan_trip_use_case() -> PlanTripUseCase:
    return PlanTripUseCase(
        geocoder=NominatimGeocoder(),
        router=OsrmRouter(),
        weather=OpenMeteoWeather(),
        repository=DjangoPlanRepository(),
        clock=SystemClock(),
        config=PlanTripConfig(max_trip_days=settings.MAX_TRIP_DAYS),
    )


def build_heatmap_use_case() -> HeatmapUseCase:
    return HeatmapUseCase(
        repository=DjangoPlanRepository(),
        weather=OpenMeteoWeather(),
        cache=DjangoFrameCache(),
        config=HeatmapConfig(max_hours=settings.MAX_FORECAST_HOURS),
    )
