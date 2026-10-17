from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return {
            RiskLevel.LOW: "Low",
            RiskLevel.MODERATE: "Moderate",
            RiskLevel.HIGH: "High",
            RiskLevel.SEVERE: "Severe",
            RiskLevel.NO_TRAVEL: "No Travel",
        }[self]


@dataclass(frozen=True, slots=True)
class GeoPoint:
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not -90 <= self.lat <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= self.lon <= 180:
            raise ValueError("Longitude must be between -180 and 180")


@dataclass(frozen=True, slots=True)
class Place:
    label: str
    point: GeoPoint


@dataclass(frozen=True, slots=True)
class RouteSegment:
    points: tuple[GeoPoint, ...]
    distance_miles: float
    duration_minutes: float

    def __post_init__(self) -> None:
        if self.distance_miles < 0 or self.duration_minutes < 0:
            raise ValueError("Route segment values cannot be negative")


@dataclass(frozen=True, slots=True)
class RouteOption:
    id: str
    label: str
    segments: tuple[RouteSegment, ...]
    distance_miles: float
    duration_minutes: float

    @property
    def geometry(self) -> tuple[GeoPoint, ...]:
        points: list[GeoPoint] = []
        for segment in self.segments:
            for point in segment.points:
                if not points or points[-1] != point:
                    points.append(point)
        return tuple(points)


@dataclass(frozen=True, slots=True)
class Weather:
    wind_mph: float
    rain_in_per_hour: float
    snow_in_per_hour: float
    temperature_f: float | None = None


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CheckpointSample:
    mile: float
    point: GeoPoint
    eta: datetime
    covered_miles: float


@dataclass(frozen=True, slots=True)
class Checkpoint:
    mile: float
    point: GeoPoint
    eta: datetime
    covered_miles: float
    weather: Weather
    risk: RiskAssessment


@dataclass(frozen=True, slots=True)
class RiskTotals:
    low_miles: float
    moderate_miles: float
    high_miles: float
    severe_miles: float
    no_travel_miles: float
    total_miles: float
    average_risk: float
    max_risk: RiskLevel

    def miles_for(self, level: RiskLevel) -> float:
        return {
            RiskLevel.LOW: self.low_miles,
            RiskLevel.MODERATE: self.moderate_miles,
            RiskLevel.HIGH: self.high_miles,
            RiskLevel.SEVERE: self.severe_miles,
            RiskLevel.NO_TRAVEL: self.no_travel_miles,
        }[level]


@dataclass(frozen=True, slots=True)
class RouteAnalysis:
    route: RouteOption
    checkpoints: tuple[Checkpoint, ...]
    totals: RiskTotals


@dataclass(frozen=True, slots=True)
class Recommendation:
    route_id: str
    rationale: str
    ranked_route_ids: tuple[str, ...]
