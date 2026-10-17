from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.trips.domain.checkpoints import (
    analyze_route,
    build_checkpoint_samples,
)
from apps.trips.domain.entities import GeoPoint, RouteOption, RouteSegment, Weather
from apps.trips.domain.risk import RiskLevel, assess_weather


def straight_route(
    first_miles: float = 100,
    second_miles: float = 50,
    first_minutes: float = 120,
    second_minutes: float = 60,
) -> RouteOption:
    first = RouteSegment(
        points=(GeoPoint(0, 0), GeoPoint(0, 0.5), GeoPoint(0, 1)),
        distance_miles=first_miles,
        duration_minutes=first_minutes,
    )
    second = RouteSegment(
        points=(GeoPoint(0, 1), GeoPoint(0, 1.5)),
        distance_miles=second_miles,
        duration_minutes=second_minutes,
    )
    return RouteOption(
        id="route-a",
        label="Route A",
        segments=(first, second),
        distance_miles=first_miles + second_miles,
        duration_minutes=first_minutes + second_minutes,
    )


def test_samples_every_interval_plus_the_destination() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    samples = build_checkpoint_samples(straight_route(), departure, 25)

    assert [sample.mile for sample in samples] == [25, 50, 75, 100, 125, 150]
    assert [sample.covered_miles for sample in samples] == [25, 25, 25, 25, 25, 25]
    assert [int((sample.eta - departure).total_seconds() / 60) for sample in samples] == [
        30,
        60,
        90,
        120,
        150,
        180,
    ]


def test_sample_points_are_interpolated_along_the_geometry() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    samples = build_checkpoint_samples(straight_route(), departure, 25)
    by_mile = {sample.mile: sample.point for sample in samples}

    assert by_mile[25].lon == pytest.approx(0.25)
    assert by_mile[125].lon == pytest.approx(1.25)
    assert by_mile[150].lon == pytest.approx(1.5)


def test_last_sample_is_clamped_to_the_destination() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    route = straight_route(second_miles=40, second_minutes=48)
    samples = build_checkpoint_samples(route, departure, 25)

    assert [sample.mile for sample in samples] == [25, 50, 75, 100, 125, 140]
    assert samples[-1].covered_miles == 15
    assert samples[-1].point.lon == pytest.approx(1.5)
    assert samples[-1].eta == departure + timedelta(minutes=168)


def test_short_route_gets_one_destination_sample() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    route = straight_route(first_miles=12, second_miles=0, first_minutes=20, second_minutes=0)
    route = RouteOption(
        id=route.id,
        label=route.label,
        segments=(route.segments[0],),
        distance_miles=12,
        duration_minutes=20,
    )
    samples = build_checkpoint_samples(route, departure, 25)

    assert len(samples) == 1
    assert samples[0].mile == 12
    assert samples[0].covered_miles == 12
    assert samples[0].eta == departure + timedelta(minutes=20)


def test_zero_distance_segments_are_ignored() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    route = straight_route()
    zero = RouteSegment(points=(GeoPoint(0, 1.5),), distance_miles=0, duration_minutes=0)
    route = RouteOption(
        id=route.id,
        label=route.label,
        segments=(*route.segments, zero),
        distance_miles=150,
        duration_minutes=180,
    )
    samples = build_checkpoint_samples(route, departure, 50)

    assert [sample.mile for sample in samples] == [50, 100, 150]


def test_analyze_route_builds_weighted_risk_totals() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    route = straight_route(first_miles=30, second_miles=10, first_minutes=36, second_minutes=12)
    samples = build_checkpoint_samples(route, departure, 10)
    weather = [Weather(0, 0, 0, 70)] * len(samples)
    weather[1] = Weather(30, 0, 0, 70)
    weather[2] = Weather(40, 0, 0, 70)
    weather[3] = Weather(50, 0, 0, 70)

    analysis = analyze_route(route, samples, weather, load_lb=10_000)

    assert analysis.totals.low_miles == 10
    assert analysis.totals.moderate_miles == 10
    assert analysis.totals.high_miles == 10
    assert analysis.totals.severe_miles == 10
    assert analysis.totals.no_travel_miles == 0
    assert analysis.totals.total_miles == 40
    assert analysis.totals.average_risk == pytest.approx(1.5)
    assert analysis.totals.max_risk is RiskLevel.SEVERE


def test_analyze_route_applies_load_rules() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    samples = build_checkpoint_samples(straight_route(), departure, 50)
    weather = [Weather(40, 0, 0, 70)] * len(samples)

    light = analyze_route(straight_route(), samples, weather, load_lb=38_000)
    heavy = analyze_route(straight_route(), samples, weather, load_lb=42_000)

    assert light.totals.high_miles == 150
    assert heavy.totals.severe_miles == 150


def test_risk_assessment_is_attached_to_each_checkpoint() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    samples = build_checkpoint_samples(straight_route(), departure, 50)
    weather = [Weather(60, 0, 0, 70)] * len(samples)

    analysis = analyze_route(straight_route(), samples, weather, load_lb=0)

    assert all(cp.risk.level is RiskLevel.NO_TRAVEL for cp in analysis.checkpoints)
    assert analysis.totals.no_travel_miles == 150


def test_assess_weather_is_the_single_source_of_risk() -> None:
    departure = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    route = straight_route(first_miles=50, second_miles=0, first_minutes=60, second_minutes=0)
    route = RouteOption(
        id=route.id,
        label=route.label,
        segments=(route.segments[0],),
        distance_miles=50,
        duration_minutes=60,
    )
    samples = build_checkpoint_samples(route, departure, 50)
    weather = Weather(36, 0, 0, 70)

    analysis = analyze_route(route, samples, [weather], load_lb=41_000)

    assert analysis.checkpoints[0].risk == assess_weather(weather, load_lb=41_000)
