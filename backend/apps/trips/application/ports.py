from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from apps.trips.domain.entities import GeoPoint, Place, RouteOption, Weather


@dataclass(frozen=True, slots=True)
class HourlyWeather:
    observed_at: datetime
    weather: Weather


class Geocoder(Protocol):
    def geocode(self, query: str) -> Place: ...


class RoutingProvider(Protocol):
    def routes(self, origin: GeoPoint, destination: GeoPoint) -> tuple[RouteOption, ...]: ...


class WeatherProvider(Protocol):
    def hourly_series(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
    ) -> tuple[tuple[HourlyWeather, ...], ...]: ...


class PlanRepository(Protocol):
    def save(self, context: PlanContext) -> None: ...

    def get(self, plan_id: UUID) -> PlanContext | None: ...


class FrameCache(Protocol):
    def get(self, key: str) -> object | None: ...

    def set(self, key: str, value: object, timeout: int) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class RouteSnapshot:
    id: str
    label: str
    distance_miles: float
    duration_minutes: float
    geometry: tuple[GeoPoint, ...]


@dataclass(frozen=True, slots=True)
class PlanContext:
    plan_id: UUID
    origin: Place
    destination: Place
    departure: datetime
    load_lb: float
    interval_miles: int
    routes: tuple[RouteSnapshot, ...]
    created_at: datetime
