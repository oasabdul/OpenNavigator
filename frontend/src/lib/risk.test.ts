import { describe, expect, it } from "vitest";

import type { RouteTotals } from "../types";
import { riskDescriptor, riskScore, riskSegments, riskSummary } from "./risk";

const totals: RouteTotals = {
  lowMiles: 60,
  moderateMiles: 20,
  highMiles: 10,
  severeMiles: 5,
  noTravelMiles: 5,
  totalMiles: 100,
  averageRisk: 1.5,
  maxRisk: "no_travel",
  maxRiskLabel: "No Travel",
};

describe("risk helpers", () => {
  it("builds weighted risk segments", () => {
    const segments = riskSegments(totals);
    expect(segments.map((segment) => segment.level)).toEqual([
      "low",
      "moderate",
      "high",
      "severe",
      "no_travel",
    ]);
    expect(segments[0]?.percent).toBe(60);
    expect(segments.reduce((sum, segment) => sum + segment.percent, 0)).toBe(100);
  });

  it("omits zero-mile segments", () => {
    const segments = riskSegments({ ...totals, moderateMiles: 0 });
    expect(segments.some((segment) => segment.level === "moderate")).toBe(false);
  });

  it("converts average risk to a 0-100 score", () => {
    expect(riskScore(0)).toBe(0);
    expect(riskScore(2)).toBe(50);
    expect(riskScore(4)).toBe(100);
  });

  it("describes average risk", () => {
    expect(riskDescriptor(0.1)).toBe("low");
    expect(riskDescriptor(0.8)).toBe("moderate");
    expect(riskDescriptor(1.8)).toBe("high");
    expect(riskDescriptor(3)).toBe("severe");
  });

  it("summarizes the most important exposure", () => {
    expect(riskSummary(totals)).toBe("5.0 no-travel mi");
    expect(riskSummary({ ...totals, noTravelMiles: 0, severeMiles: 2 })).toBe("2.0 severe mi");
    expect(
      riskSummary({
        ...totals,
        noTravelMiles: 0,
        severeMiles: 0,
        highMiles: 0,
      }),
    ).toBe("No severe weather exposure");
  });
});
