from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.trips.application.errors import InvalidTripRequest, LocationNotFound, UpstreamUnavailable
from apps.trips.application.heatmap import HeatmapUseCase
from apps.trips.application.models import PlanTripCommand
from apps.trips.application.plan_trip import PlanTripUseCase
from apps.trips.tests.fakes import (
    FakeCache,
    FakeClock,
    FakeGeocoder,
    FakeRepository,
    FakeRouter,
    FakeWeather,
)


@pytest.fixture
def planned_trip():
    repository = FakeRepository()
    use_case = PlanTripUseCase(
        geocoder=FakeGeocoder(),
        router=FakeRouter(),
        weather=FakeWeather(),
        repository=repository,
        clock=FakeClock(),
    )
    result = use_case.execute(
        PlanTripCommand(
            origin_query="origin",
            destination_query="destination",
            departure=datetime(2026, 10, 18, 6, 0, tzinfo=UTC),
            load_lb=38_000,
            interval_miles=25,
        )
    )
    weather = FakeWeather()
    heatmap = HeatmapUseCase(
        repository=repository,
        weather=weather,
        cache=FakeCache(),
    )
    return SimpleNamespace(result=result, repository=repository, heatmap=heatmap)


@pytest.fixture
def client():
    return APIClient()


def test_health_endpoint(client) -> None:
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_endpoint(client) -> None:
    response = client.get("/api/v1/config/")
    assert response.status_code == 200
    assert response.json()["samplingIntervalsMiles"] == [10, 25, 50]
    assert response.json()["forecastHours"] == 48


def test_plan_endpoint_returns_routes_checkpoints_and_recommendation(client, planned_trip) -> None:
    with patch(
        "apps.trips.interface.views.build_plan_trip_use_case",
        return_value=SimpleNamespace(execute=lambda command: planned_trip.result),
    ):
        response = client.post(
            "/api/v1/trips/plan/",
            {
                "origin": "origin",
                "destination": "destination",
                "departure": "2026-10-18T06:00:00Z",
                "load_weight_lb": 38_000,
                "sampling_interval_miles": 25,
            },
            format="json",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["planId"] == str(planned_trip.result.plan_id)
    assert len(payload["routes"]) == 3
    assert len(payload["routes"][0]["checkpoints"]) == 40
    assert payload["routes"][0]["checkpoints"][0]["weather"]["windMph"] == 10.0
    assert payload["recommendation"]["routeId"] == "a"
    assert payload["routes"][0]["geometry"][0] == [38.0, -100.0]
    assert payload["warnings"] == []


def test_plan_endpoint_validates_input(client) -> None:
    response = client.post(
        "/api/v1/trips/plan/",
        {"origin": "x", "destination": "destination"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert "departure" in response.json()["error"]["fields"]


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (InvalidTripRequest("bad"), 400, "invalid_trip"),
        (LocationNotFound("missing"), 422, "location_not_found"),
        (UpstreamUnavailable("down"), 502, "upstream_unavailable"),
    ],
)
def test_plan_endpoint_maps_application_errors(client, error, status, code) -> None:
    def fail(command):
        raise error

    with patch(
        "apps.trips.interface.views.build_plan_trip_use_case",
        return_value=SimpleNamespace(execute=fail),
    ):
        response = client.post(
            "/api/v1/trips/plan/",
            {
                "origin": "origin",
                "destination": "destination",
                "departure": "2026-10-18T06:00:00Z",
                "load_weight_lb": 10_000,
            },
            format="json",
        )

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_heatmap_endpoint_returns_a_frame(client, planned_trip) -> None:
    with patch(
        "apps.trips.interface.views.build_heatmap_use_case",
        return_value=planned_trip.heatmap,
    ):
        response = client.get(
            f"/api/v1/trips/{planned_trip.result.plan_id}/heatmap/",
            {"route_id": "a", "hour": 12},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["hour"] == 12
    assert payload["routeId"] == "a"
    assert len(payload["points"]) >= 15
    assert response["Cache-Control"] == "public, max-age=300"
    assert payload["points"][0]["risk"]["level"] in {
        "low",
        "moderate",
        "high",
        "severe",
        "no_travel",
    }


def test_heatmap_endpoint_returns_gone_for_expired_plans(client, planned_trip) -> None:
    with patch(
        "apps.trips.interface.views.build_heatmap_use_case",
        return_value=planned_trip.heatmap,
    ):
        response = client.get(
            f"/api/v1/trips/{uuid4()}/heatmap/",
            {"route_id": "a", "hour": 0},
        )

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "plan_not_found"


def test_heatmap_endpoint_rejects_invalid_hours(client, planned_trip) -> None:
    response = client.get(
        f"/api/v1/trips/{planned_trip.result.plan_id}/heatmap/",
        {"route_id": "a", "hour": 49},
    )
    assert response.status_code == 400
