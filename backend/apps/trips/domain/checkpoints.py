from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from apps.trips.domain.entities import (
    Checkpoint,
    CheckpointSample,
    RiskLevel,
    RiskTotals,
    RouteAnalysis,
    RouteOption,
    Weather,
)
from apps.trips.domain.geo import point_at_fraction
from apps.trips.domain.risk import assess_weather

_EPSILON = 1e-9
SUPPORTED_INTERVALS = (10, 25, 50)


def build_checkpoint_samples(
    route: RouteOption,
    departure: datetime,
    interval_miles: int,
) -> tuple[CheckpointSample, ...]:
    if interval_miles not in SUPPORTED_INTERVALS:
        raise ValueError(f"Sampling interval must be one of {SUPPORTED_INTERVALS}")
    if route.distance_miles <= 0:
        raise ValueError("Route distance must be greater than zero")

    total_miles = route.distance_miles
    samples: list[CheckpointSample] = []
    previous_mile = 0.0
    target_mile = float(interval_miles)
    segment_start_mile = 0.0
    segment_start_minutes = 0.0

    for segment in route.segments:
        if segment.distance_miles <= 0:
            continue
        segment_end_mile = segment_start_mile + segment.distance_miles
        while target_mile <= segment_end_mile + _EPSILON and target_mile <= total_miles + _EPSILON:
            fraction = (target_mile - segment_start_mile) / segment.distance_miles
            fraction = max(0.0, min(1.0, fraction))
            eta = departure + timedelta(
                minutes=segment_start_minutes + fraction * segment.duration_minutes
            )
            samples.append(
                CheckpointSample(
                    mile=target_mile,
                    point=point_at_fraction(segment.points, fraction),
                    eta=eta,
                    covered_miles=target_mile - previous_mile,
                )
            )
            previous_mile = target_mile
            target_mile += interval_miles
        segment_start_mile = segment_end_mile
        segment_start_minutes += segment.duration_minutes

    if not samples or samples[-1].mile < total_miles - 1e-6:
        geometry = route.geometry
        if not geometry:
            raise ValueError("Route has no geometry")
        samples.append(
            CheckpointSample(
                mile=total_miles,
                point=geometry[-1],
                eta=departure + timedelta(minutes=route.duration_minutes),
                covered_miles=total_miles - previous_mile,
            )
        )

    return tuple(samples)


def summarize_risk(checkpoints: Sequence[Checkpoint]) -> RiskTotals:
    miles = {level: 0.0 for level in RiskLevel}
    weighted_risk = 0.0
    total_miles = 0.0
    max_risk = RiskLevel.LOW

    for checkpoint in checkpoints:
        covered = checkpoint.covered_miles
        miles[checkpoint.risk.level] += covered
        weighted_risk += checkpoint.risk.level.value * covered
        total_miles += covered
        max_risk = max(max_risk, checkpoint.risk.level)

    return RiskTotals(
        low_miles=miles[RiskLevel.LOW],
        moderate_miles=miles[RiskLevel.MODERATE],
        high_miles=miles[RiskLevel.HIGH],
        severe_miles=miles[RiskLevel.SEVERE],
        no_travel_miles=miles[RiskLevel.NO_TRAVEL],
        total_miles=total_miles,
        average_risk=weighted_risk / total_miles if total_miles else 0.0,
        max_risk=max_risk,
    )


def analyze_route(
    route: RouteOption,
    samples: Sequence[CheckpointSample],
    weather: Sequence[Weather],
    load_lb: float,
) -> RouteAnalysis:
    if len(samples) != len(weather):
        raise ValueError("Every checkpoint sample needs exactly one weather observation")

    checkpoints = tuple(
        Checkpoint(
            mile=sample.mile,
            point=sample.point,
            eta=sample.eta,
            covered_miles=sample.covered_miles,
            weather=observation,
            risk=assess_weather(observation, load_lb),
        )
        for sample, observation in zip(samples, weather, strict=True)
    )

    return RouteAnalysis(
        route=route,
        checkpoints=checkpoints,
        totals=summarize_risk(checkpoints),
    )
