from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from apps.trips.application.errors import LocationNotFound, UpstreamUnavailable
from apps.trips.application.ports import HourlyWeather, PlanContext
from apps.trips.domain.entities import GeoPoint, Place, RouteOption, RouteSegment, Weather


def straight_route(
    route_id: str,
    *,
    lat: float = 38.0,
    distance_miles: float = 1000,
    duration_minutes: float = 600,
) -> RouteOption:
    segment = RouteSegment(
        points=(GeoPoint(lat, -100), GeoPoint(lat, -90)),
        distance_miles=distance_miles,
        duration_minutes=duration_minutes,
    )
    return RouteOption(
        id=route_id,
        label=f"Route {route_id}",
        segments=(segment,),
        distance_miles=distance_miles,
        duration_minutes=duration_minutes,
    )


class FakeGeocoder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def geocode(self, query: str) -> Place:
        self.calls.append(query)
        if query.lower() == "origin":
            return Place(label="Origin, TX", point=GeoPoint(38.0, -100.0))
        if query.lower() == "destination":
            return Place(label="Destination, TN", point=GeoPoint(38.0, -90.0))
        if query.lower() == "same":
            return Place(label="Same", point=GeoPoint(38.0, -100.0))
        raise LocationNotFound("Unknown test location")


class FakeRouter:
    def __init__(self, routes: tuple[RouteOption, ...] | None = None) -> None:
        self._routes = routes or (
            straight_route("a", lat=38.0, distance_miles=1000, duration_minutes=600),
            straight_route("b", lat=39.0, distance_miles=1050, duration_minutes=700),
            straight_route("c", lat=40.0, distance_miles=1100, duration_minutes=800),
        )
        self.calls = 0

    def routes(self, origin: GeoPoint, destination: GeoPoint) -> tuple[RouteOption, ...]:
        self.calls += 1
        return self._routes


class FakeWeather:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def hourly_series(self, points, start: datetime, end: datetime):
        self.calls += 1
        if self.fail:
            raise UpstreamUnavailable("weather failed")
        hours = int((end - start).total_seconds() // 3600) + 1
        result = []
        for point in points:
            if point.lat < 38.5:
                wind = 10.0
            elif point.lat < 39.5:
                wind = 40.0
            else:
                wind = 50.0
            result.append(
                tuple(
                    HourlyWeather(
                        observed_at=start + timedelta(hours=hour),
                        weather=Weather(
                            wind_mph=wind,
                            rain_in_per_hour=0,
                            snow_in_per_hour=0,
                            temperature_f=65,
                        ),
                    )
                    for hour in range(hours)
                )
            )
        return tuple(result)


class FakeRepository:
    def __init__(self) -> None:
        self.contexts: dict[UUID, PlanContext] = {}

    def save(self, context: PlanContext) -> None:
        self.contexts[context.plan_id] = context

    def get(self, plan_id: UUID) -> PlanContext | None:
        return self.contexts.get(plan_id)


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self.values.get(key)

    def set(self, key: str, value: object, timeout: int) -> None:
        self.values[key] = value


class FakeClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 10, 18, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now
