from __future__ import annotations

from datetime import timedelta

from apps.trips.application.errors import (
    InvalidTripRequest,
    PlanNotFound,
    UpstreamUnavailable,
)
from apps.trips.application.models import (
    HeatmapCommand,
    HeatmapConfig,
    HeatmapDataset,
    HeatmapFrame,
    HeatmapPoint,
)
from apps.trips.application.plan_trip import floor_hour, weather_at
from apps.trips.application.ports import (
    FrameCache,
    PlanRepository,
    WeatherProvider,
)
from apps.trips.domain.geo import sample_polyline
from apps.trips.domain.risk import assess_weather


class HeatmapUseCase:
    def __init__(
        self,
        *,
        repository: PlanRepository,
        weather: WeatherProvider,
        cache: FrameCache,
        config: HeatmapConfig | None = None,
    ) -> None:
        self._repository = repository
        self._weather = weather
        self._cache = cache
        self._config = config or HeatmapConfig()

    def execute(self, command: HeatmapCommand) -> HeatmapFrame:
        if not 0 <= command.hour <= self._config.max_hours:
            raise InvalidTripRequest(
                f"Forecast hour must be between 0 and {self._config.max_hours}"
            )

        context = self._repository.get(command.plan_id)
        if context is None:
            raise PlanNotFound("This trip plan has expired. Plan the trip again.")

        route = next((item for item in context.routes if item.id == command.route_id), None)
        if route is None:
            raise PlanNotFound("Route not found in this trip plan")

        cache_key = f"heatmap:{context.plan_id}:{route.id}"
        dataset = self._cache.get(cache_key)
        if not isinstance(dataset, HeatmapDataset):
            dataset = self._build_dataset(context, route, cache_key)
        return dataset.frames[command.hour]

    def _build_dataset(self, context, route, cache_key: str) -> HeatmapDataset:
        points = sample_polyline(
            route.geometry,
            self._config.interval_miles,
            max_points=self._config.max_points,
        )
        if not points:
            raise PlanNotFound("This route has no usable geometry")

        start = floor_hour(context.departure)
        end = start + timedelta(hours=self._config.max_hours)
        series = self._weather.hourly_series(points, start, end)
        if len(series) != len(points):
            raise UpstreamUnavailable("Weather service returned an incomplete corridor forecast")

        frames: list[HeatmapFrame] = []
        for hour in range(self._config.max_hours + 1):
            forecast_time = start + timedelta(hours=hour)
            frame_points = []
            for point, point_series in zip(points, series, strict=True):
                weather = weather_at(point_series, forecast_time).weather
                frame_points.append(
                    HeatmapPoint(
                        point=point,
                        weather=weather,
                        risk=assess_weather(weather, context.load_lb),
                    )
                )
            frames.append(
                HeatmapFrame(
                    hour=hour,
                    forecast_time=forecast_time,
                    points=tuple(frame_points),
                )
            )

        dataset = HeatmapDataset(
            plan_id=context.plan_id,
            route_id=route.id,
            departure=context.departure,
            frames=tuple(frames),
        )
        self._cache.set(cache_key, dataset, self._config.cache_seconds)
        return dataset

