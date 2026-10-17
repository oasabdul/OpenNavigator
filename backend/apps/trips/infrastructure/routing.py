from __future__ import annotations

import logging
import math
from collections.abc import Callable

import requests
from django.conf import settings
from django.core.cache import cache

from apps.trips.application.errors import NoRoutesFound, UpstreamUnavailable
from apps.trips.domain.entities import GeoPoint, RouteOption, RouteSegment
from apps.trips.domain.geo import EARTH_RADIUS_MILES, point_at_fraction
from apps.trips.infrastructure.http import request_json

METERS_PER_MILE = 1609.344
logger = logging.getLogger(__name__)


def _bearing(start: GeoPoint, end: GeoPoint) -> float:
    lat1 = math.radians(start.lat)
    lat2 = math.radians(end.lat)
    dlon = math.radians(end.lon - start.lon)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360


def _destination(start: GeoPoint, bearing_degrees: float, miles: float) -> GeoPoint:
    angular = miles / EARTH_RADIUS_MILES
    bearing = math.radians(bearing_degrees)
    lat1 = math.radians(start.lat)
    lon1 = math.radians(start.lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular) + math.cos(lat1) * math.sin(angular) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular) * math.cos(lat1),
        math.cos(angular) - math.sin(lat1) * math.sin(lat2),
    )
    return GeoPoint(
        lat=math.degrees(lat2),
        lon=(math.degrees(lon2) + 540) % 360 - 180,
    )


class OsrmRouter:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float | None = None,
        http_get: Callable[..., requests.Response] = requests.get,
    ) -> None:
        self._base_url = (base_url or settings.OSRM_BASE_URL).rstrip("/")
        self._user_agent = user_agent or settings.HTTP_USER_AGENT
        self._timeout = timeout or settings.UPSTREAM_TIMEOUT_SECONDS
        self._http_get = http_get

    def routes(self, origin: GeoPoint, destination: GeoPoint) -> tuple[RouteOption, ...]:
        cache_key = (
            "routes:"
            f"{origin.lat:.4f},{origin.lon:.4f}:"
            f"{destination.lat:.4f},{destination.lon:.4f}"
        )
        cached = cache.get(cache_key)
        if isinstance(cached, tuple) and all(isinstance(item, RouteOption) for item in cached):
            return cached

        payload = self._request([origin, destination], alternatives=3)
        raw_routes = payload.get("routes") or []
        if not raw_routes:
            raise NoRoutesFound("No drivable route was found between these places")

        routes = [
            self._parse_route(raw_route, f"Route {index + 1}")
            for index, raw_route in enumerate(raw_routes[:3])
        ]
        routes = self._deduplicate(routes)
        if len(routes) < 3:
            routes = self._add_detour_routes(routes, origin, destination)

        result = tuple(routes[:3])
        if not result:
            raise NoRoutesFound("No drivable route was found between these places")
        cache.set(cache_key, result, timeout=1800)
        return result

    def _request(
        self,
        points: list[GeoPoint],
        *,
        alternatives: int | bool,
    ) -> dict:
        coordinates = ";".join(f"{point.lon:.6f},{point.lat:.6f}" for point in points)
        params = {
            "overview": "full",
            "steps": "true",
            "geometries": "geojson",
            "continue_straight": "false",
        }
        if alternatives is not False:
            params["alternatives"] = str(alternatives)

        try:
            payload = request_json(
                self._http_get,
                f"{self._base_url}/route/v1/driving/{coordinates}",
                params=params,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "application/json",
                },
                timeout=self._timeout,
            )
        except (requests.RequestException, ValueError) as exc:
            logger.warning("OSRM request failed: %s", exc)
            raise UpstreamUnavailable(
                "The routing service is unavailable. Try again in a moment."
            ) from exc

        if payload.get("code") != "Ok":
            message = payload.get("message") or "The routing service could not build a route"
            raise NoRoutesFound(message)
        return payload

    def _add_detour_routes(
        self,
        routes: list[RouteOption],
        origin: GeoPoint,
        destination: GeoPoint,
    ) -> list[RouteOption]:
        if not routes:
            return routes
        primary = min(routes, key=lambda route: route.duration_minutes)
        if len(primary.geometry) < 2 or primary.distance_miles <= 0:
            return routes

        midpoint = point_at_fraction(primary.geometry, 0.5)
        heading = _bearing(primary.geometry[0], primary.geometry[-1])
        offset = min(25.0, max(2.5, primary.distance_miles * 0.02))

        for distance in (offset, offset * 1.8):
            for side in (1, -1):
                if len(routes) >= 3:
                    return routes
                via = _destination(midpoint, heading + side * 90, distance)
                try:
                    payload = self._request([origin, via, destination], alternatives=False)
                except (NoRoutesFound, UpstreamUnavailable):
                    continue
                raw_routes = payload.get("routes") or []
                if not raw_routes:
                    continue
                candidate = self._parse_route(
                    raw_routes[0], f"Route {len(routes) + 1}"
                )
                if candidate.duration_minutes > primary.duration_minutes * 2.5:
                    continue
                if candidate.distance_miles > primary.distance_miles * 2.5:
                    continue
                routes = self._deduplicate([*routes, candidate])
        return routes

    def _parse_route(self, raw: dict, label: str) -> RouteOption:
        segments: list[RouteSegment] = []
        pending_minutes = 0.0

        try:
            for leg in raw.get("legs") or []:
                for step in leg.get("steps") or []:
                    distance = float(step.get("distance") or 0) / METERS_PER_MILE
                    duration = float(step.get("duration") or 0) / 60
                    coordinates = (
                        (step.get("geometry") or {}).get("coordinates") or []
                    )
                    if distance <= 0 or len(coordinates) < 2:
                        pending_minutes += duration
                        continue
                    duration += pending_minutes
                    pending_minutes = 0.0
                    segments.append(
                        RouteSegment(
                            points=tuple(
                                GeoPoint(lat=float(lat), lon=float(lon))
                                for lon, lat in coordinates
                            ),
                            distance_miles=distance,
                            duration_minutes=duration,
                        )
                    )
        except (TypeError, ValueError) as exc:
            raise UpstreamUnavailable("The routing service returned invalid geometry") from exc

        if pending_minutes and segments:
            last = segments[-1]
            segments[-1] = RouteSegment(
                points=last.points,
                distance_miles=last.distance_miles,
                duration_minutes=last.duration_minutes + pending_minutes,
            )

        if not segments:
            coordinates = (raw.get("geometry") or {}).get("coordinates") or []
            if len(coordinates) < 2:
                raise UpstreamUnavailable("The routing service returned an empty route")
            segments.append(
                RouteSegment(
                    points=tuple(
                        GeoPoint(lat=float(lat), lon=float(lon)) for lon, lat in coordinates
                    ),
                    distance_miles=float(raw.get("distance") or 0) / METERS_PER_MILE,
                    duration_minutes=float(raw.get("duration") or 0) / 60,
                )
            )

        distance = float(raw.get("distance") or 0) / METERS_PER_MILE
        duration = float(raw.get("duration") or 0) / 60
        return RouteOption(
            id=label.lower().replace(" ", "-"),
            label=label,
            segments=tuple(segments),
            distance_miles=distance,
            duration_minutes=duration,
        )

    @staticmethod
    def _deduplicate(routes: list[RouteOption]) -> list[RouteOption]:
        unique: list[RouteOption] = []
        fingerprints: set[tuple[tuple[float, float], ...]] = set()
        for route in routes:
            geometry = route.geometry
            if not geometry:
                continue
            indices = sorted(
                {
                    0,
                    len(geometry) // 4,
                    len(geometry) // 2,
                    (3 * len(geometry)) // 4,
                    len(geometry) - 1,
                }
            )
            fingerprint = tuple(
                (round(geometry[index].lat, 3), round(geometry[index].lon, 3))
                for index in indices
            )
            if fingerprint not in fingerprints:
                fingerprints.add(fingerprint)
                unique.append(route)
        return unique
