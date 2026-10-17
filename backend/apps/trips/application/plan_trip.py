from __future__ import annotations

from bisect import bisect_right
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.trips.application.errors import (
    InvalidTripRequest,
    NoRoutesFound,
    UpstreamUnavailable,
)
from apps.trips.application.models import PlanTripCommand, PlanTripConfig, TripPlanResult
from apps.trips.application.ports import (
    Clock,
    Geocoder,
    HourlyWeather,
    PlanContext,
    PlanRepository,
    RouteSnapshot,
    RoutingProvider,
    WeatherProvider,
)
from apps.trips.domain.checkpoints import analyze_route, build_checkpoint_samples
from apps.trips.domain.entities import CheckpointSample, RouteOption, Weather
from apps.trips.domain.geo import haversine_miles
from apps.trips.domain.recommendation import recommend_routes

MIN_SEPARATION_MILES = 0.25


def floor_hour(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def ceil_hour(value: datetime) -> datetime:
    floored = floor_hour(value)
    return floored if floored == value.astimezone(UTC) else floored + timedelta(hours=1)


def weather_at(series: tuple[HourlyWeather, ...], at: datetime) -> HourlyWeather:
    if not series:
        raise UpstreamUnavailable("Weather forecast did not include the requested corridor")
    target = floor_hour(at)
    times = [entry.observed_at for entry in series]
    index = bisect_right(times, target) - 1
    index = max(0, min(index, len(series) - 1))
    return series[index]


class PlanTripUseCase:
    def __init__(
        self,
        *,
        geocoder: Geocoder,
        router: RoutingProvider,
        weather: WeatherProvider,
        repository: PlanRepository,
        clock: Clock,
        config: PlanTripConfig | None = None,
    ) -> None:
        self._geocoder = geocoder
        self._router = router
        self._weather = weather
        self._repository = repository
        self._clock = clock
        self._config = config or PlanTripConfig()

    def execute(self, command: PlanTripCommand) -> TripPlanResult:
        self._validate(command)
        departure = command.departure.astimezone(UTC)
        now = self._clock.now().astimezone(UTC)

        if departure < now - timedelta(minutes=self._config.clock_skew_minutes):
            raise InvalidTripRequest("Departure time cannot be in the past")
        if departure > now + timedelta(days=self._config.max_trip_days):
            raise InvalidTripRequest(
                f"Forecast data is available for departures up to {self._config.max_trip_days} days ahead"
            )

        origin = self._geocoder.geocode(command.origin_query)
        destination = self._geocoder.geocode(command.destination_query)
        if haversine_miles(origin.point, destination.point) < MIN_SEPARATION_MILES:
            raise InvalidTripRequest("Origin and destination must be different places")

        routes = self._normalise_routes(
            self._router.routes(origin.point, destination.point)
        )
        if not routes:
            raise NoRoutesFound("No drivable routes were found between these places")

        samples_by_route = []
        for route in routes:
            try:
                samples = build_checkpoint_samples(route, departure, command.interval_miles)
            except ValueError as exc:
                raise NoRoutesFound(f"Route geometry was unusable: {exc}") from exc
            samples_by_route.append(samples)

        weather_by_checkpoint = self._weather_for_checkpoints(samples_by_route)
        analyses = [
            analyze_route(
                route,
                samples,
                tuple(
                    weather_by_checkpoint[(route_index, sample_index)]
                    for sample_index in range(len(samples))
                ),
                command.load_lb,
            )
            for route_index, (route, samples) in enumerate(
                zip(routes, samples_by_route, strict=True)
            )
        ]

        recommendation = recommend_routes(analyses)
        warnings: list[str] = []
        if len(analyses) < 3:
            warnings.append(
                f"Only {len(analyses)} distinct route option(s) are available for this corridor."
            )

        result = TripPlanResult(
            plan_id=uuid4(),
            origin=origin,
            destination=destination,
            departure=departure,
            load_lb=command.load_lb,
            interval_miles=command.interval_miles,
            analyses=tuple(analyses),
            recommendation=recommendation,
            generated_at=now,
            warnings=tuple(warnings),
        )
        self._repository.save(
            PlanContext(
                plan_id=result.plan_id,
                origin=origin,
                destination=destination,
                departure=departure,
                load_lb=command.load_lb,
                interval_miles=command.interval_miles,
                routes=tuple(
                    RouteSnapshot(
                        id=analysis.route.id,
                        label=analysis.route.label,
                        distance_miles=analysis.route.distance_miles,
                        duration_minutes=analysis.route.duration_minutes,
                        geometry=analysis.route.geometry,
                    )
                    for analysis in analyses
                ),
                created_at=now,
            )
        )
        return result

    def _weather_for_checkpoints(
        self, samples_by_route: list[tuple[CheckpointSample, ...]]
    ) -> dict[tuple[int, int], Weather]:
        groups: dict[datetime, list[tuple[int, int, object]]] = {}
        for route_index, samples in enumerate(samples_by_route):
            for sample_index, sample in enumerate(samples):
                eta_hour = floor_hour(sample.eta)
                bucket_start = eta_hour.replace(hour=(eta_hour.hour // 6) * 6)
                groups.setdefault(bucket_start, []).append(
                    (route_index, sample_index, sample)
                )

        weather_by_checkpoint: dict[tuple[int, int], Weather] = {}
        for bucket_start, entries in groups.items():
            points_by_key = {}
            for _route_index, _sample_index, sample in entries:
                key = (round(sample.point.lat, 5), round(sample.point.lon, 5))
                points_by_key[key] = sample.point
            points = list(points_by_key.values())
            series = self._weather.hourly_series(
                points,
                bucket_start,
                bucket_start + timedelta(hours=5),
            )
            if len(series) != len(points):
                raise UpstreamUnavailable(
                    "Weather service returned an incomplete forecast"
                )
            series_by_key = dict(zip(points_by_key, series, strict=True))
            for route_index, sample_index, sample in entries:
                key = (round(sample.point.lat, 5), round(sample.point.lon, 5))
                weather_by_checkpoint[(route_index, sample_index)] = weather_at(
                    series_by_key[key], sample.eta
                ).weather
        return weather_by_checkpoint

    @staticmethod
    def _validate(command: PlanTripCommand) -> None:
        if len(command.origin_query.strip()) < 2:
            raise InvalidTripRequest("Origin is required")
        if len(command.destination_query.strip()) < 2:
            raise InvalidTripRequest("Destination is required")
        if command.departure.tzinfo is None:
            raise InvalidTripRequest("Departure must include a timezone")
        if command.load_lb < 0 or command.load_lb > 200_000:
            raise InvalidTripRequest("Load weight must be between 0 and 200,000 lb")
        if command.interval_miles not in (10, 25, 50):
            raise InvalidTripRequest("Sampling interval must be 10, 25, or 50 miles")

    @staticmethod
    def _normalise_routes(routes: tuple[RouteOption, ...]) -> tuple[RouteOption, ...]:
        normalised: list[RouteOption] = []
        seen: set[str] = set()
        for index, route in enumerate(routes):
            if route.distance_miles <= 0:
                continue
            route_id = route.id if route.id not in seen else f"{route.id}-{index + 1}"
            seen.add(route_id)
            if route_id != route.id:
                route = RouteOption(
                    id=route_id,
                    label=route.label,
                    segments=route.segments,
                    distance_miles=route.distance_miles,
                    duration_minutes=route.duration_minutes,
                )
            normalised.append(route)
        return tuple(normalised[:3])
