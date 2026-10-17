import type { RiskLevel, RouteOption } from "../types";

const EARTH_RADIUS_MILES = 3958.7613;

export type Position = [number, number];

export interface RiskPolyline {
  level: RiskLevel;
  positions: Position[];
}

export function haversineMiles(start: Position, end: Position): number {
  const toRadians = Math.PI / 180;
  const lat1 = start[0] * toRadians;
  const lat2 = end[0] * toRadians;
  const deltaLat = lat2 - lat1;
  const deltaLon = (end[1] - start[1]) * toRadians;
  const a =
    Math.sin(deltaLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
  return 2 * EARTH_RADIUS_MILES * Math.asin(Math.min(1, Math.sqrt(a)));
}

function clampFraction(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function interpolate(start: Position, end: Position, fraction: number): Position {
  return [
    start[0] + (end[0] - start[0]) * fraction,
    start[1] + (end[1] - start[1]) * fraction,
  ];
}

function pushUnique(positions: Position[], position: Position): void {
  const last = positions[positions.length - 1];
  if (!last || last[0] !== position[0] || last[1] !== position[1]) {
    positions.push(position);
  }
}

export function sliceGeometry(
  geometry: Position[],
  startFraction: number,
  endFraction: number,
): Position[] {
  if (geometry.length < 2) return geometry.slice();
  const start = clampFraction(Math.min(startFraction, endFraction));
  const end = clampFraction(Math.max(startFraction, endFraction));
  if (start === 0 && end === 1) return geometry.slice();
  if (end <= start) return [];

  const cumulative: number[] = [0];
  for (let index = 1; index < geometry.length; index += 1) {
    const previous = geometry[index - 1];
    const current = geometry[index];
    if (!previous || !current) continue;
    cumulative.push((cumulative[index - 1] ?? 0) + haversineMiles(previous, current));
  }
  const total = cumulative[cumulative.length - 1] ?? 0;
  if (total <= 0) return geometry.slice(0, 1);

  const targetStart = total * start;
  const targetEnd = total * end;
  const result: Position[] = [];

  for (let index = 1; index < geometry.length; index += 1) {
    const segmentStart = cumulative[index - 1] ?? 0;
    const segmentEnd = cumulative[index] ?? 0;
    const from = geometry[index - 1];
    const to = geometry[index];
    if (!from || !to) continue;
    if (segmentEnd < targetStart || segmentStart > targetEnd) continue;

    const length = segmentEnd - segmentStart;
    if (result.length === 0) {
      const fraction = length <= 0 ? 0 : (targetStart - segmentStart) / length;
      pushUnique(result, interpolate(from, to, clampFraction(fraction)));
    }

    if (segmentEnd >= targetEnd) {
      const fraction = length <= 0 ? 0 : (targetEnd - segmentStart) / length;
      pushUnique(result, interpolate(from, to, clampFraction(fraction)));
      break;
    }

    pushUnique(result, to);
  }

  return result;
}

export function routeRiskPolylines(route: RouteOption): RiskPolyline[] {
  if (route.checkpoints.length === 0) {
    return [{ level: route.totals.maxRisk, positions: route.geometry }];
  }
  const total = route.distanceMiles || route.totals.totalMiles || 1;
  const polylines: RiskPolyline[] = [];
  let previousMile = 0;

  for (const checkpoint of route.checkpoints) {
    const startFraction = previousMile / total;
    const endFraction = checkpoint.mile / total;
    const positions = sliceGeometry(route.geometry, startFraction, endFraction);
    if (positions.length >= 2) {
      const last = polylines[polylines.length - 1];
      if (last && last.level === checkpoint.risk.level) {
        for (const position of positions) pushUnique(last.positions, position);
      } else {
        polylines.push({ level: checkpoint.risk.level, positions });
      }
    }
    previousMile = checkpoint.mile;
  }

  if (previousMile < total - 0.1) {
    const last = polylines[polylines.length - 1];
    const positions = sliceGeometry(route.geometry, previousMile / total, 1);
    if (positions.length >= 2) {
      if (last) {
        for (const position of positions) pushUnique(last.positions, position);
      } else {
        polylines.push({ level: route.totals.maxRisk, positions });
      }
    }
  }

  return polylines;
}

export function routeBounds(route: RouteOption): [[number, number], [number, number]] {
  const points = route.geometry.length > 0 ? route.geometry : route.checkpoints.map((cp) => [cp.lat, cp.lon] as Position);
  let minLat = 90;
  let maxLat = -90;
  let minLon = 180;
  let maxLon = -180;
  for (const [lat, lon] of points) {
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
  }
  return [
    [minLat, minLon],
    [maxLat, maxLon],
  ];
}

export function planBounds(routes: RouteOption[]): [[number, number], [number, number]] {
  const bounds = routes.map(routeBounds);
  if (bounds.length === 0) {
    return [
      [24, -125],
      [49, -66],
    ];
  }
  return [
    [
      Math.min(...bounds.map((bound) => bound[0][0])),
      Math.min(...bounds.map((bound) => bound[0][1])),
    ],
    [
      Math.max(...bounds.map((bound) => bound[1][0])),
      Math.max(...bounds.map((bound) => bound[1][1])),
    ],
  ];
}

export function fastestRouteId(routes: RouteOption[]): string | null {
  if (routes.length === 0) return null;
  return routes.reduce((fastest, route) =>
    route.durationMinutes < fastest.durationMinutes ? route : fastest,
  ).id;
}
