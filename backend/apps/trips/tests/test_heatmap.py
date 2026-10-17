from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from apps.trips.application.errors import InvalidTripRequest, PlanNotFound
from apps.trips.application.heatmap import HeatmapUseCase
from apps.trips.application.models import HeatmapCommand
from apps.trips.application.ports import HourlyWeather, PlanContext, RouteSnapshot
from apps.trips.domain.entities import GeoPoint, Place, RiskLevel, Weather
from apps.trips.tests.fakes import FakeCache, FakeRepository, FakeWeather


def context(load_lb: float = 42_000) -> PlanContext:
    return PlanContext(
        plan_id=uuid4(),
        origin=Place(label="Origin", point=GeoPoint(38, -100)),
        destination=Place(label="Destination", point=GeoPoint(38, -90)),
        departure=datetime(2026, 10, 18, 6, 20, tzinfo=UTC),
        load_lb=load_lb,
        interval_miles=25,
        routes=(
            RouteSnapshot(
                id="route-1",
                label="Route 1",
                distance_miles=520,
                duration_minutes=600,
                geometry=(
                    GeoPoint(38, -100),
                    GeoPoint(38, -95),
                    GeoPoint(38, -90),
                ),
            ),
        ),
        created_at=datetime(2026, 10, 18, 6, 0, tzinfo=UTC),
    )


def build_use_case(plan_context: PlanContext | None = None, weather=None):
    repository = FakeRepository()
    plan_context = plan_context or context()
    repository.save(plan_context)
    weather = weather or FakeWeather()
    cache = FakeCache()
    return (
        HeatmapUseCase(repository=repository, weather=weather, cache=cache),
        plan_context,
        weather,
        cache,
    )


class HighWindWeather:
    def __init__(self, wind_mph: float = 45.0) -> None:
        self.wind_mph = wind_mph
        self.calls = 0

    def hourly_series(self, points, start, end):
        self.calls += 1
        hours = int((end - start).total_seconds() // 3600) + 1
        return tuple(
            tuple(
                HourlyWeather(
                    observed_at=start + timedelta(hours=hour),
                    weather=Weather(
                        wind_mph=self.wind_mph,
                        rain_in_per_hour=0,
                        snow_in_per_hour=0,
                    ),
                )
                for hour in range(hours)
            )
            for _ in points
        )


def test_heatmap_returns_a_corridor_frame_for_the_requested_hour() -> None:
    use_case, plan, _, _ = build_use_case()
    frame = use_case.execute(HeatmapCommand(plan.plan_id, "route-1", 0))

    assert frame.hour == 0
    assert frame.forecast_time == datetime(2026, 10, 18, 6, 0, tzinfo=UTC)
    assert len(frame.points) >= 15
    assert all(point.risk.level is RiskLevel.LOW for point in frame.points)


def test_heatmap_starts_at_the_departure_hour_and_runs_for_48_hours() -> None:
    use_case, plan, _, _ = build_use_case()
    first = use_case.execute(HeatmapCommand(plan.plan_id, "route-1", 0))
    last = use_case.execute(HeatmapCommand(plan.plan_id, "route-1", 48))

    assert first.forecast_time.hour == 6
    assert last.forecast_time == datetime(2026, 10, 20, 6, 0, tzinfo=UTC)


def test_heatmap_dataset_is_cached_between_slider_frames() -> None:
    use_case, plan, weather, _ = build_use_case()
    use_case.execute(HeatmapCommand(plan.plan_id, "route-1", 0))
    use_case.execute(HeatmapCommand(plan.plan_id, "route-1", 1))
    use_case.execute(HeatmapCommand(plan.plan_id, "route-1", 24))

    assert weather.calls == 1


def test_heatmap_applies_load_rules_to_corridor_points() -> None:
    use_case, plan, _, _ = build_use_case(
        context(load_lb=42_000), weather=HighWindWeather(45.0)
    )
    frame = use_case.execute(HeatmapCommand(plan.plan_id, "route-1", 0))

    assert all(point.risk.level is RiskLevel.NO_TRAVEL for point in frame.points)


def test_heatmap_rejects_an_unknown_plan() -> None:
    use_case, _, _, _ = build_use_case()
    with pytest.raises(PlanNotFound):
        use_case.execute(HeatmapCommand(uuid4(), "route-1", 0))


def test_heatmap_rejects_an_unknown_route() -> None:
    use_case, plan, _, _ = build_use_case()
    with pytest.raises(PlanNotFound):
        use_case.execute(HeatmapCommand(plan.plan_id, "route-x", 0))


@pytest.mark.parametrize("hour", [-1, 49])
def test_heatmap_rejects_out_of_range_hours(hour: int) -> None:
    use_case, plan, _, _ = build_use_case()
    with pytest.raises(InvalidTripRequest):
        use_case.execute(HeatmapCommand(plan.plan_id, "route-1", hour))
