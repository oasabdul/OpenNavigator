import { describe, expect, it } from "vitest";

import type { Checkpoint, RouteOption } from "../types";
import {
  fastestRouteId,
  planBounds,
  routeBounds,
  routeRiskPolylines,
  sliceGeometry,
} from "./route";

function checkpoint(mile: number, level: Checkpoint["risk"]["level"]): Checkpoint {
  return {
    mile,
    coveredMiles: 25,
    lat: 0,
    lon: mile / 50,
    eta: "2026-10-18T12:00:00Z",
    weather: { windMph: 10, rainInPerHour: 0, snowInPerHour: 0, temperatureF: 65 },
    risk: { level, label: level, reasons: [] },
  };
}

function route(overrides: Partial<RouteOption> = {}): RouteOption {
  return {
    id: "route-1",
    label: "Route 1",
    distanceMiles: 100,
    durationMinutes: 120,
    geometry: [
      [0, 0],
      [0, 1],
      [0, 2],
    ],
    checkpoints: [checkpoint(25, "low"), checkpoint(50, "high"), checkpoint(75, "low"), checkpoint(100, "low")],
    totals: {
      lowMiles: 75,
      moderateMiles: 0,
      highMiles: 25,
      severeMiles: 0,
      noTravelMiles: 0,
      totalMiles: 100,
      averageRisk: 0.5,
      maxRisk: "high",
      maxRiskLabel: "High",
    },
    ...overrides,
  };
}

describe("route helpers", () => {
  it("slices geometry between mileage fractions", () => {
    const slice = sliceGeometry(
      [
        [0, 0],
        [0, 1],
        [0, 2],
      ],
      0.25,
      0.5,
    );
    expect(slice[0]?.[1]).toBeCloseTo(0.5, 5);
    expect(slice[slice.length - 1]?.[1]).toBeCloseTo(1, 5);
  });

  it("builds risk-colored polylines and merges adjacent equal risk", () => {
    const polylines = routeRiskPolylines(route());
    expect(polylines.map((polyline) => polyline.level)).toEqual(["low", "high", "low"]);
    expect(polylines[0]?.positions[0]).toEqual([0, 0]);
    expect(polylines[2]?.positions.at(-1)).toEqual([0, 2]);
  });

  it("computes bounds and the fastest route", () => {
    const first = route();
    const second = route({ id: "route-2", durationMinutes: 90, geometry: [[1, -2], [2, 3]] });
    expect(routeBounds(first)).toEqual([
      [0, 0],
      [0, 2],
    ]);
    expect(planBounds([first, second])).toEqual([
      [0, -2],
      [2, 3],
    ]);
    expect(fastestRouteId([first, second])).toBe("route-2");
  });
});
