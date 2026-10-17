from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.trips.application.ports import PlanContext
from apps.trips.domain.entities import (
    GeoPoint,
    Place,
    Recommendation,
    RiskAssessment,
    RouteAnalysis,
    Weather,
)


@dataclass(frozen=True, slots=True)
class PlanTripCommand:
    origin_query: str
    destination_query: str
    departure: datetime
    load_lb: float
    interval_miles: int


@dataclass(frozen=True, slots=True)
class TripPlanResult:
    plan_id: UUID
    origin: Place
    destination: Place
    departure: datetime
    load_lb: float
    interval_miles: int
    analyses: tuple[RouteAnalysis, ...]
    recommendation: Recommendation
    generated_at: datetime
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanTripConfig:
    max_trip_days: int = 14
    clock_skew_minutes: int = 5


@dataclass(frozen=True, slots=True)
class HeatmapCommand:
    plan_id: UUID
    route_id: str
    hour: int


@dataclass(frozen=True, slots=True)
class HeatmapPoint:
    point: GeoPoint
    weather: Weather
    risk: RiskAssessment


@dataclass(frozen=True, slots=True)
class HeatmapFrame:
    hour: int
    forecast_time: datetime
    points: tuple[HeatmapPoint, ...]


@dataclass(frozen=True, slots=True)
class HeatmapDataset:
    plan_id: UUID
    route_id: str
    departure: datetime
    frames: tuple[HeatmapFrame, ...]


@dataclass(frozen=True, slots=True)
class HeatmapConfig:
    interval_miles: float = 10.0
    max_hours: int = 48
    cache_seconds: int = 3600
    max_points: int = 16


__all__ = [
    "HeatmapCommand",
    "HeatmapConfig",
    "HeatmapDataset",
    "HeatmapFrame",
    "HeatmapPoint",
    "PlanContext",
    "PlanTripCommand",
    "PlanTripConfig",
    "TripPlanResult",
]
