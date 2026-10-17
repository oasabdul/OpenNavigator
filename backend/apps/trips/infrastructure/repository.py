from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.utils import timezone

from apps.trips.application.ports import PlanContext, RouteSnapshot
from apps.trips.domain.entities import GeoPoint, Place
from apps.trips.infrastructure.models import TripPlanRecord


class DjangoPlanRepository:
    def save(self, context: PlanContext) -> None:
        expires_at = context.created_at + timedelta(hours=settings.PLAN_RETENTION_HOURS)
        TripPlanRecord.objects.update_or_create(
            id=context.plan_id,
            defaults={
                "created_at": context.created_at,
                "expires_at": expires_at,
                "context": self._serialize(context),
            },
        )
        TripPlanRecord.objects.filter(expires_at__lt=timezone.now()).delete()

    def get(self, plan_id: UUID) -> PlanContext | None:
        record = TripPlanRecord.objects.filter(
            id=plan_id,
            expires_at__gt=timezone.now(),
        ).first()
        if record is None:
            return None
        return self._deserialize(record.context)

    @staticmethod
    def _serialize(context: PlanContext) -> dict:
        return {
            "plan_id": str(context.plan_id),
            "origin": {
                "label": context.origin.label,
                "lat": context.origin.point.lat,
                "lon": context.origin.point.lon,
            },
            "destination": {
                "label": context.destination.label,
                "lat": context.destination.point.lat,
                "lon": context.destination.point.lon,
            },
            "departure": context.departure.isoformat(),
            "load_lb": context.load_lb,
            "interval_miles": context.interval_miles,
            "created_at": context.created_at.isoformat(),
            "routes": [
                {
                    "id": route.id,
                    "label": route.label,
                    "distance_miles": route.distance_miles,
                    "duration_minutes": route.duration_minutes,
                    "geometry": [[point.lat, point.lon] for point in route.geometry],
                }
                for route in context.routes
            ],
        }

    @staticmethod
    def _deserialize(payload: dict) -> PlanContext:
        origin = payload["origin"]
        destination = payload["destination"]
        return PlanContext(
            plan_id=UUID(payload["plan_id"]),
            origin=Place(
                label=origin["label"],
                point=GeoPoint(lat=origin["lat"], lon=origin["lon"]),
            ),
            destination=Place(
                label=destination["label"],
                point=GeoPoint(lat=destination["lat"], lon=destination["lon"]),
            ),
            departure=datetime.fromisoformat(payload["departure"]),
            load_lb=payload["load_lb"],
            interval_miles=payload["interval_miles"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            routes=tuple(
                RouteSnapshot(
                    id=route["id"],
                    label=route["label"],
                    distance_miles=route["distance_miles"],
                    duration_minutes=route["duration_minutes"],
                    geometry=tuple(
                        GeoPoint(lat=point[0], lon=point[1]) for point in route["geometry"]
                    ),
                )
                for route in payload["routes"]
            ),
        )
