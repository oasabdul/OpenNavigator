from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from apps.trips.application.ports import PlanContext, RouteSnapshot
from apps.trips.domain.entities import GeoPoint, Place
from apps.trips.infrastructure.models import TripPlanRecord
from apps.trips.infrastructure.repository import DjangoPlanRepository


def make_context() -> PlanContext:
    return PlanContext(
        plan_id=uuid4(),
        origin=Place(label="Origin", point=GeoPoint(38.0, -100.0)),
        destination=Place(label="Destination", point=GeoPoint(38.0, -90.0)),
        departure=datetime(2026, 10, 18, 6, 0, tzinfo=UTC),
        load_lb=38_000,
        interval_miles=25,
        routes=(
            RouteSnapshot(
                id="route-1",
                label="Route 1",
                distance_miles=520.5,
                duration_minutes=600.25,
                geometry=(
                    GeoPoint(38.0, -100.0),
                    GeoPoint(38.0, -95.0),
                    GeoPoint(38.0, -90.0),
                ),
            ),
        ),
        created_at=timezone.now(),
    )


@pytest.mark.django_db
def test_plan_round_trips_through_the_database() -> None:
    repository = DjangoPlanRepository()
    context = make_context()

    repository.save(context)
    loaded = repository.get(context.plan_id)

    assert loaded == context
    assert TripPlanRecord.objects.count() == 1


@pytest.mark.django_db
def test_expired_plans_are_not_returned() -> None:
    repository = DjangoPlanRepository()
    context = make_context()
    repository.save(context)
    TripPlanRecord.objects.filter(id=context.plan_id).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    assert repository.get(context.plan_id) is None


@pytest.mark.django_db
def test_unknown_plan_returns_none() -> None:
    assert DjangoPlanRepository().get(uuid4()) is None


@pytest.mark.django_db
def test_expired_plans_are_purged_when_a_new_plan_is_saved() -> None:
    repository = DjangoPlanRepository()
    old = make_context()
    repository.save(old)
    TripPlanRecord.objects.filter(id=old.plan_id).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    repository.save(make_context())

    assert not TripPlanRecord.objects.filter(id=old.plan_id).exists()
