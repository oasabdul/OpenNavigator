from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import requests

from apps.trips.application.errors import LocationNotFound, NoRoutesFound, UpstreamUnavailable
from apps.trips.domain.entities import GeoPoint, RouteOption
from apps.trips.infrastructure.geocoding import NominatimGeocoder
from apps.trips.infrastructure.routing import OsrmRouter
from apps.trips.infrastructure.weather import OpenMeteoWeather


class FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_geocoder_returns_a_place_and_caches_the_result() -> None:
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            [
                {
                    "display_name": "New York, New York, United States",
                    "lat": "40.7128",
                    "lon": "-74.0060",
                }
            ]
        )

    geocoder = NominatimGeocoder(
        base_url="https://nominatim.test",
        user_agent="test-agent",
        timeout=5,
        http_get=fake_get,
        min_interval_seconds=0,
    )

    first = geocoder.geocode("New York, NY")
    second = geocoder.geocode("new york, ny")

    assert first.point.lat == pytest.approx(40.7128)
    assert first.label.startswith("New York")
    assert second == first
    assert len(calls) == 1
    assert calls[0][1]["headers"]["User-Agent"] == "test-agent"


def test_geocoder_accepts_coordinate_pairs_without_an_http_call() -> None:
    def fail(*args, **kwargs):
        raise AssertionError("HTTP should not be called")

    geocoder = NominatimGeocoder(http_get=fail, min_interval_seconds=0)
    place = geocoder.geocode("40.7128, -74.0060")

    assert place.point == GeoPoint(40.7128, -74.006)
    assert "40.71280" in place.label


def test_geocoder_rejects_unknown_locations() -> None:
    geocoder = NominatimGeocoder(
        http_get=lambda *args, **kwargs: FakeResponse([]),
        min_interval_seconds=0,
    )
    with pytest.raises(LocationNotFound):
        geocoder.geocode("Atlantis")


def test_geocoder_maps_http_failures_to_upstream_errors() -> None:
    geocoder = NominatimGeocoder(
        http_get=lambda *args, **kwargs: FakeResponse({}, status_code=503),
        min_interval_seconds=0,
    )
    with pytest.raises(UpstreamUnavailable):
        geocoder.geocode("New York")


def raw_route(mid_lat: float, *, include_zero_step: bool = False) -> dict:
    coordinates = [[-100.0, 38.0], [-95.0, mid_lat], [-90.0, 38.0]]
    steps = [
        {
            "distance": 1609.344,
            "duration": 3600,
            "geometry": {"coordinates": coordinates[:2]},
        }
    ]
    if include_zero_step:
        steps.append(
            {
                "distance": 0,
                "duration": 1800,
                "geometry": {"coordinates": [coordinates[1]]},
            }
        )
    steps.append(
        {
            "distance": 3218.688,
            "duration": 7200,
            "geometry": {"coordinates": coordinates[1:]},
        }
    )
    return {
        "distance": 4828.032,
        "duration": 12600,
        "legs": [{"steps": steps}],
        "geometry": {"coordinates": coordinates},
    }


def test_osrm_parser_builds_segments_and_preserves_time_on_zero_distance_steps() -> None:
    router = OsrmRouter(http_get=lambda *args, **kwargs: FakeResponse({}))
    route = router._parse_route(raw_route(39.0, include_zero_step=True), "Route 1")

    assert route.distance_miles == pytest.approx(3.0)
    assert len(route.segments) == 2
    assert route.segments[0].duration_minutes == pytest.approx(60)
    assert route.segments[1].duration_minutes == pytest.approx(150)
    assert route.geometry[0] == GeoPoint(38, -100)


def test_osrm_adds_detour_routes_until_three_options_exist() -> None:
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs["params"]))
        if kwargs["params"].get("alternatives") == "3":
            return FakeResponse(
                {"code": "Ok", "routes": [raw_route(39.0), raw_route(36.0)]}
            )
        return FakeResponse({"code": "Ok", "routes": [raw_route(44.0)]})

    router = OsrmRouter(
        base_url="https://osrm.test",
        user_agent="test-agent",
        timeout=5,
        http_get=fake_get,
    )
    routes = router.routes(GeoPoint(38, -100), GeoPoint(38, -90))

    assert len(routes) == 3
    assert all(isinstance(route, RouteOption) for route in routes)
    assert [route.id for route in routes] == ["route-1", "route-2", "route-3"]
    assert len(calls) >= 2


def test_osrm_maps_invalid_payloads_to_upstream_errors() -> None:
    router = OsrmRouter(
        http_get=lambda *args, **kwargs: FakeResponse({"code": "InvalidQuery"})
    )
    with pytest.raises(NoRoutesFound):
        router.routes(GeoPoint(38, -100), GeoPoint(38, -90))


def weather_item(times: list[str], *, missing_rain: bool = False) -> dict:
    count = len(times)
    return {
        "hourly": {
            "time": times,
            "wind_speed_10m": [10.0 + index for index in range(count)],
            "rain": [None if missing_rain and index == 0 else 0.2 for index in range(count)],
            "snowfall": [0.0 for _ in range(count)],
            "temperature_2m": [65.0 for _ in range(count)],
        }
    }


def test_weather_provider_parses_batches_and_preserves_input_order() -> None:
    times = [
        "2026-10-18T06:00",
        "2026-10-18T07:00",
        "2026-10-18T08:00",
    ]
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs["params"])
        return FakeResponse(
            [
                weather_item(times),
                weather_item(times, missing_rain=True),
            ]
        )

    weather = OpenMeteoWeather(
        base_url="https://weather.test",
        user_agent="test-agent",
        timeout=5,
        http_get=fake_get,
        batch_size=100,
    )
    points = [GeoPoint(38, -100), GeoPoint(38, -100), GeoPoint(39, -95)]
    series = weather.hourly_series(
        points,
        datetime(2026, 10, 18, 6, 0, tzinfo=UTC),
        datetime(2026, 10, 18, 8, 0, tzinfo=UTC),
    )

    assert len(series) == 3
    assert series[0] == series[1]
    assert series[0][0].weather.wind_mph == 10
    assert series[2][0].weather.rain_in_per_hour == 0
    assert series[2][0].observed_at == datetime(2026, 10, 18, 6, 0, tzinfo=UTC)
    assert len(calls) == 1
    assert calls[0]["precipitation_unit"] == "inch"
    assert calls[0]["wind_speed_unit"] == "mph"


def test_weather_provider_caches_series() -> None:
    times = ["2026-10-18T06:00"]
    calls = []

    def fake_get(url, **kwargs):
        calls.append(1)
        return FakeResponse(weather_item(times))

    weather = OpenMeteoWeather(
        http_get=fake_get,
        timeout=5,
        batch_size=100,
    )
    point = GeoPoint(38, -100)
    start = datetime(2026, 10, 18, 6, 0, tzinfo=UTC)
    weather.hourly_series([point], start, start)
    weather.hourly_series([point], start, start)

    assert len(calls) == 1


def test_weather_provider_rejects_incomplete_payloads() -> None:
    weather = OpenMeteoWeather(
        http_get=lambda *args, **kwargs: FakeResponse({"hourly": {"time": []}}),
        timeout=5,
    )
    with pytest.raises(UpstreamUnavailable):
        weather.hourly_series(
            [GeoPoint(38, -100)],
            datetime(2026, 10, 18, 6, 0, tzinfo=UTC),
            datetime(2026, 10, 18, 7, 0, tzinfo=UTC),
        )


def test_weather_provider_window_is_utc_hour_aligned() -> None:
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs["params"])
        return FakeResponse(weather_item(["2026-10-18T06:00"]))

    weather = OpenMeteoWeather(http_get=fake_get, timeout=5)
    weather.hourly_series(
        [GeoPoint(38, -100)],
        datetime(2026, 10, 18, 6, 0, tzinfo=UTC) + timedelta(minutes=40),
        datetime(2026, 10, 18, 7, 0, tzinfo=UTC),
    )

    assert calls[0]["start_hour"] == "2026-10-18T06:00"
    assert calls[0]["end_hour"] == "2026-10-18T07:00"
