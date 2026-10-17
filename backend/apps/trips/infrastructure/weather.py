from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

from apps.trips.application.errors import UpstreamUnavailable
from apps.trips.application.ports import HourlyWeather
from apps.trips.domain.entities import GeoPoint, Weather
from apps.trips.infrastructure.http import request_json

BATCH_SIZE = 40
logger = logging.getLogger(__name__)


class OpenMeteoWeather:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float | None = None,
        http_get: Callable[..., requests.Response] = requests.get,
        batch_size: int = BATCH_SIZE,
        max_workers: int = 6,
    ) -> None:
        self._base_url = (base_url or settings.OPEN_METEO_BASE_URL).rstrip("/")
        self._user_agent = user_agent or settings.HTTP_USER_AGENT
        self._timeout = timeout or settings.UPSTREAM_TIMEOUT_SECONDS
        self._http_get = http_get
        self._batch_size = batch_size
        self._max_workers = max_workers

    def hourly_series(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
    ) -> tuple[tuple[HourlyWeather, ...], ...]:
        if not points:
            return ()
        start = start.astimezone(UTC)
        end = end.astimezone(UTC)
        if end < start:
            raise UpstreamUnavailable("Invalid weather forecast window")

        unique: list[GeoPoint] = []
        index_by_key: dict[tuple[float, float], int] = {}
        original_indexes: list[int] = []
        for point in points:
            key = (round(point.lat, 5), round(point.lon, 5))
            if key not in index_by_key:
                index_by_key[key] = len(unique)
                unique.append(point)
            original_indexes.append(index_by_key[key])

        window = start.strftime("%Y-%m-%dT%H:00")
        window_end = end.strftime("%Y-%m-%dT%H:00")
        cache_keys = [
            f"weather:{point.lat:.5f}:{point.lon:.5f}:{window}:{window_end}"
            for point in unique
        ]
        series_by_unique: list[tuple[HourlyWeather, ...] | None] = [
            cache.get(key) for key in cache_keys
        ]

        missing = [
            index for index, series in enumerate(series_by_unique) if not isinstance(series, tuple)
        ]
        batches = [
            missing[index : index + self._batch_size]
            for index in range(0, len(missing), self._batch_size)
        ]
        if batches:
            with ThreadPoolExecutor(max_workers=min(self._max_workers, len(batches))) as executor:
                results = list(
                    executor.map(
                        lambda batch: self._fetch(unique, batch, start, end),
                        batches,
                    )
                )
            for batch, batch_series in zip(batches, results, strict=True):
                for index, series in zip(batch, batch_series, strict=True):
                    series_by_unique[index] = series
                    cache.set(cache_keys[index], series, timeout=900)

        return tuple(
            series_by_unique[index] or () for index in original_indexes
        )

    def _fetch(
        self,
        unique: list[GeoPoint],
        batch: list[int],
        start: datetime,
        end: datetime,
    ) -> tuple[tuple[HourlyWeather, ...], ...]:
        params = {
            "latitude": ",".join(f"{unique[index].lat:.5f}" for index in batch),
            "longitude": ",".join(f"{unique[index].lon:.5f}" for index in batch),
            "hourly": "wind_speed_10m,rain,snowfall,temperature_2m",
            "wind_speed_unit": "mph",
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "start_hour": start.strftime("%Y-%m-%dT%H:00"),
            "end_hour": end.strftime("%Y-%m-%dT%H:00"),
        }
        try:
            payload = request_json(
                self._http_get,
                f"{self._base_url}/forecast",
                params=params,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "application/json",
                },
                timeout=max(self._timeout, 30),
            )
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Open-Meteo request failed: %s", exc)
            raise UpstreamUnavailable(
                "The weather service is unavailable. Try again in a moment."
            ) from exc

        if isinstance(payload, dict):
            items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            raise UpstreamUnavailable("The weather service returned an invalid response")
        if len(items) != len(batch):
            raise UpstreamUnavailable("The weather service returned incomplete data")

        return tuple(self._parse_item(item) for item in items)

    @staticmethod
    def _parse_item(item: dict) -> tuple[HourlyWeather, ...]:
        try:
            hourly = item["hourly"]
            times = hourly["time"]
            wind = hourly["wind_speed_10m"]
            rain = hourly["rain"]
            snow = hourly["snowfall"]
            temperature = hourly.get("temperature_2m", [None] * len(times))
        except (KeyError, TypeError) as exc:
            raise UpstreamUnavailable("The weather service returned incomplete data") from exc

        if not (len(times) == len(wind) == len(rain) == len(snow) == len(temperature)):
            raise UpstreamUnavailable("The weather service returned incomplete data")

        series = []
        for index, timestamp in enumerate(times):
            try:
                observed_at = datetime.fromisoformat(timestamp).replace(tzinfo=UTC)
                weather = Weather(
                    wind_mph=float(wind[index] or 0),
                    rain_in_per_hour=float(rain[index] or 0),
                    snow_in_per_hour=float(snow[index] or 0),
                    temperature_f=(
                        float(temperature[index]) if temperature[index] is not None else None
                    ),
                )
            except (TypeError, ValueError) as exc:
                raise UpstreamUnavailable(
                    "The weather service returned invalid data"
                ) from exc
            series.append(HourlyWeather(observed_at=observed_at, weather=weather))
        return tuple(series)
