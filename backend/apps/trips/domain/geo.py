from __future__ import annotations

import math

from apps.trips.domain.entities import GeoPoint

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(start: GeoPoint, end: GeoPoint) -> float:
    lat1 = math.radians(start.lat)
    lat2 = math.radians(end.lat)
    dlat = lat2 - lat1
    dlon = math.radians(end.lon - start.lon)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def interpolate(start: GeoPoint, end: GeoPoint, fraction: float) -> GeoPoint:
    fraction = max(0.0, min(1.0, fraction))
    return GeoPoint(
        lat=start.lat + (end.lat - start.lat) * fraction,
        lon=start.lon + (end.lon - start.lon) * fraction,
    )


def point_at_fraction(points: tuple[GeoPoint, ...], fraction: float) -> GeoPoint:
    if not points:
        raise ValueError("A route segment needs at least one point")
    if len(points) == 1:
        return points[0]
    fraction = max(0.0, min(1.0, fraction))
    if fraction == 1:
        return points[-1]

    lengths = [haversine_miles(a, b) for a, b in zip(points, points[1:], strict=False)]
    total = sum(lengths)
    if total == 0:
        return points[0]

    target = total * fraction
    traversed = 0.0
    for (start, end), length in zip(zip(points, points[1:], strict=False), lengths, strict=False):
        if traversed + length >= target:
            within = 0.0 if length == 0 else (target - traversed) / length
            return interpolate(start, end, within)
        traversed += length
    return points[-1]


def sample_polyline(
    points: tuple[GeoPoint, ...],
    interval_miles: float,
    *,
    max_points: int = 600,
) -> tuple[GeoPoint, ...]:
    if not points:
        return ()
    if len(points) == 1 or interval_miles <= 0:
        return (points[0],)

    lengths = [haversine_miles(a, b) for a, b in zip(points, points[1:], strict=False)]
    total = sum(lengths)
    if total <= 0:
        return (points[0],)

    spacing = max(interval_miles, total / max_points)
    targets = [0.0]
    target = spacing
    while target < total - 1e-6:
        targets.append(target)
        target += spacing
    targets.append(total)

    sampled: list[GeoPoint] = [points[0]]
    segment_index = 0
    traversed = 0.0
    for target in targets[1:]:
        while (
            segment_index < len(lengths) - 1
            and traversed + lengths[segment_index] < target
        ):
            traversed += lengths[segment_index]
            segment_index += 1
        length = lengths[segment_index]
        fraction = 0.0 if length == 0 else (target - traversed) / length
        sampled.append(
            interpolate(points[segment_index], points[segment_index + 1], fraction)
        )

    deduped = [sampled[0]]
    for point in sampled[1:]:
        if point != deduped[-1]:
            deduped.append(point)
    return tuple(deduped)

