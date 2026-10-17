from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.trips.application.errors import (
    InvalidTripRequest,
    UpstreamUnavailable,
)
from apps.trips.application.models import PlanTripCommand, PlanTripConfig
from apps.trips.application.plan_trip import PlanTripUseCase, ceil_hour, floor_hour, weather_at
from apps.trips.application.ports import HourlyWeather
from apps.trips.domain.entities import Weather
from apps.trips.tests.fakes import (
    FakeClock,
    FakeGeocoder,
    FakeRepository,
    FakeRouter,
    FakeWeather,
    straight_route,
)


def build_use_case(
    *,
    router: FakeRouter | None = None,
    weather: FakeWeather | None = None,
    clock: FakeClock | None = None,
    repository: FakeRepository | None = None,
) -> tuple[PlanTripUseCase, FakeRepository]:
    repository = repository or FakeRepository()
    use_case = PlanTripUseCase(
        geocoder=FakeGeocoder(),
        router=router or FakeRouter(),
        weather=weather or FakeWeather(),
        repository=repository,
        clock=clock or FakeClock(),
        config=PlanTripConfig(max_trip_days=14),
    )
    return use_case, repository


def command(
    *,
    origin: str = "origin",
    destination: str = "destination",
    departure: datetime | None = None,
    load_lb: float = 38_000,
    interval: int = 25,
) -> PlanTripCommand:
    return PlanTripCommand(
        origin_query=origin,
        destination_query=destination,
        departure=departure or datetime(2026, 10, 18, 6, 0, tzinfo=UTC),
        load_lb=load_lb,
        interval_miles=interval,
    )


def test_planning_returns_three_analysed_routes_and_a_recommendation() -> None:
    use_case, repository = build_use_case()
    result = use_case.execute(command())

    assert len(result.analyses) == 3
    assert result.recommendation.route_id == "a"
    assert result.recommendation.ranked_route_ids[0] == "a"
    assert result.analyses[0].totals.low_miles == 1000
    assert result.analyses[1].totals.high_miles == 1050
    assert result.analyses[2].totals.no_travel_miles == 1100
    assert "No-travel" in result.recommendation.rationale
    assert result.origin.label == "Origin, TX"
    assert result.destination.label == "Destination, TN"
    assert result.plan_id in repository.contexts
    assert len(repository.contexts[result.plan_id].routes) == 3


def test_checkpoints_use_weather_at_their_own_eta() -> None:
    class ChangingWeather(FakeWeather):
        def hourly_series(self, points, start, end):
            result = []
            for _point in points:
                result.append(
                    tuple(
                        HourlyWeather(
                            observed_at=start + timedelta(hours=hour),
                            weather=Weather(
                                wind_mph=10
                                if (start + timedelta(hours=hour)).hour < 10
                                else 40,
                                rain_in_per_hour=0,
                                snow_in_per_hour=0,
                            ),
                        )
                        for hour in range(20)
                    )
                )
            return tuple(result)

    use_case, _ = build_use_case(weather=ChangingWeather())
    result = use_case.execute(command(interval=50, load_lb=38_000))
    route = result.analyses[0]
    early = [checkpoint for checkpoint in route.checkpoints if checkpoint.eta.hour < 10]
    late = [checkpoint for checkpoint in route.checkpoints if checkpoint.eta.hour >= 10]

    assert early and all(checkpoint.risk.level.value == 0 for checkpoint in early)
    assert late and all(checkpoint.risk.level.value == 2 for checkpoint in late)


def test_weather_is_fetched_in_six_hour_buckets() -> None:
    class WindowRecorder(FakeWeather):
        def __init__(self) -> None:
            super().__init__()
            self.windows: list[tuple[datetime, datetime]] = []

        def hourly_series(self, points, start, end):
            self.windows.append((start, end))
            return super().hourly_series(points, start, end)

    weather = WindowRecorder()
    use_case, _ = build_use_case(weather=weather)
    use_case.execute(command())

    assert len(weather.windows) > 1
    assert all(end - start == timedelta(hours=5) for start, end in weather.windows)
    assert all(start.hour in (0, 6, 12, 18) for start, _end in weather.windows)


def test_short_weather_series_is_rejected() -> None:
    class ShortWeather(FakeWeather):
        def hourly_series(self, points, start, end):
            return ()

    use_case, _ = build_use_case(weather=ShortWeather())

    with pytest.raises(UpstreamUnavailable):
        use_case.execute(command())


def test_past_departure_is_rejected() -> None:
    use_case, _ = build_use_case()
    with pytest.raises(InvalidTripRequest, match="past"):
        use_case.execute(command(departure=datetime(2026, 10, 17, 6, 0, tzinfo=UTC)))


def test_departure_beyond_forecast_horizon_is_rejected() -> None:
    use_case, _ = build_use_case()
    with pytest.raises(InvalidTripRequest, match="14 days"):
        use_case.execute(command(departure=datetime(2026, 11, 10, 6, 0, tzinfo=UTC)))


def test_naive_departure_is_rejected() -> None:
    use_case, _ = build_use_case()
    with pytest.raises(InvalidTripRequest, match="timezone"):
        use_case.execute(command(departure=datetime(2026, 10, 18, 6, 0)))


def test_same_origin_and_destination_is_rejected() -> None:
    use_case, _ = build_use_case()
    with pytest.raises(InvalidTripRequest, match="different"):
        use_case.execute(command(origin="origin", destination="same"))


def test_invalid_interval_is_rejected() -> None:
    use_case, _ = build_use_case()
    with pytest.raises(InvalidTripRequest, match="interval"):
        use_case.execute(command(interval=20))


def test_invalid_load_is_rejected() -> None:
    use_case, _ = build_use_case()
    with pytest.raises(InvalidTripRequest, match="Load"):
        use_case.execute(command(load_lb=-1))


def test_two_routes_are_returned_with_a_warning() -> None:
    router = FakeRouter(
        routes=(
            straight_route("a", lat=38.0),
            straight_route("b", lat=39.0),
        )
    )
    use_case, _ = build_use_case(router=router)
    result = use_case.execute(command())

    assert len(result.analyses) == 2
    assert result.warnings
    assert "2 distinct" in result.warnings[0]


def test_duplicate_route_ids_are_normalised() -> None:
    duplicate = straight_route("a", lat=38.0)
    router = FakeRouter(
        routes=(
            duplicate,
            duplicate,
            straight_route("a", lat=40.0, distance_miles=1100, duration_minutes=800),
        )
    )
    use_case, _ = build_use_case(router=router)
    result = use_case.execute(command())

    assert len({analysis.route.id for analysis in result.analyses}) == 3


def test_weather_at_uses_the_forecast_hour_covering_the_eta() -> None:
    start = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    series = tuple(
        HourlyWeather(
            observed_at=start + timedelta(hours=hour),
            weather=Weather(wind_mph=float(hour * 10), rain_in_per_hour=0, snow_in_per_hour=0),
        )
        for hour in range(4)
    )

    assert weather_at(series, start + timedelta(hours=2, minutes=35)).weather.wind_mph == 20
    assert weather_at(series, start - timedelta(hours=2)).weather.wind_mph == 0
    assert weather_at(series, start + timedelta(days=1)).weather.wind_mph == 30


def test_hour_rounding_helpers_are_timezone_aware() -> None:
    value = datetime(2026, 10, 18, 12, 34, tzinfo=UTC)
    assert floor_hour(value) == datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    assert ceil_hour(value) == datetime(2026, 10, 18, 13, 0, tzinfo=UTC)
    exact = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
    assert ceil_hour(exact) == exact
