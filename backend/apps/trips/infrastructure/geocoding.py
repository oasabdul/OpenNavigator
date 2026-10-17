from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from collections.abc import Callable

import requests
from django.conf import settings
from django.core.cache import cache

from apps.trips.application.errors import LocationNotFound, UpstreamUnavailable
from apps.trips.domain.entities import GeoPoint, Place

logger = logging.getLogger(__name__)
_COORDINATES = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


class _RateLimiter:
    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval = min_interval_seconds
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


class NominatimGeocoder:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float | None = None,
        http_get: Callable[..., requests.Response] = requests.get,
        min_interval_seconds: float = 1.0,
    ) -> None:
        self._base_url = (base_url or settings.NOMINATIM_BASE_URL).rstrip("/")
        self._user_agent = user_agent or settings.HTTP_USER_AGENT
        self._timeout = timeout or settings.UPSTREAM_TIMEOUT_SECONDS
        self._http_get = http_get
        self._limiter = _RateLimiter(min_interval_seconds)

    def geocode(self, query: str) -> Place:
        cleaned = " ".join(query.split())
        if not cleaned:
            raise LocationNotFound("Location is required")

        coordinates = _COORDINATES.match(cleaned)
        if coordinates:
            lat, lon = float(coordinates.group(1)), float(coordinates.group(2))
            try:
                point = GeoPoint(lat=lat, lon=lon)
            except ValueError as exc:
                raise LocationNotFound(f"Invalid coordinates: {exc}") from exc
            return Place(label=f"{lat:.5f}, {lon:.5f}", point=point)

        cache_key = "geocode:" + hashlib.sha1(cleaned.lower().encode()).hexdigest()
        cached = cache.get(cache_key)
        if isinstance(cached, Place):
            return cached

        self._limiter.wait()
        try:
            response = self._http_get(
                f"{self._base_url}/search",
                params={
                    "q": cleaned,
                    "format": "jsonv2",
                    "limit": 1,
                    "addressdetails": 1,
                    "accept-language": "en",
                },
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "application/json",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Nominatim request failed: %s", exc)
            raise UpstreamUnavailable(
                "The geocoding service is unavailable. Try again in a moment."
            ) from exc

        if not isinstance(payload, list) or not payload:
            raise LocationNotFound(f"No location found for '{cleaned}'")
        item = payload[0]
        try:
            place = Place(
                label=item["display_name"],
                point=GeoPoint(lat=float(item["lat"]), lon=float(item["lon"])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamUnavailable("The geocoding service returned an invalid result") from exc

        cache.set(cache_key, place, timeout=86_400)
        return place
