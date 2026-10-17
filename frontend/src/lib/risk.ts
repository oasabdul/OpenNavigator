import type { RiskLevel, RouteTotals } from "../types";

export interface RiskMeta {
  label: string;
  color: string;
  soft: string;
  text: string;
  order: number;
}

export const RISK_ORDER: RiskLevel[] = ["low", "moderate", "high", "severe", "no_travel"];

export const RISK_META: Record<RiskLevel, RiskMeta> = {
  low: {
    label: "Low",
    color: "#1f8a5b",
    soft: "rgba(31, 138, 91, 0.16)",
    text: "#11603e",
    order: 0,
  },
  moderate: {
    label: "Moderate",
    color: "#d3a126",
    soft: "rgba(211, 161, 38, 0.18)",
    text: "#7c5b00",
    order: 1,
  },
  high: {
    label: "High",
    color: "#e06a2b",
    soft: "rgba(224, 106, 43, 0.18)",
    text: "#9a3f10",
    order: 2,
  },
  severe: {
    label: "Severe",
    color: "#c23b3b",
    soft: "rgba(194, 59, 59, 0.18)",
    text: "#8f2020",
    order: 3,
  },
  no_travel: {
    label: "No Travel",
    color: "#7c3aed",
    soft: "rgba(124, 58, 237, 0.18)",
    text: "#5b21b6",
    order: 4,
  },
};

export interface RiskSegment {
  level: RiskLevel;
  miles: number;
  percent: number;
}

export function riskSegments(totals: RouteTotals): RiskSegment[] {
  const values: Array<[RiskLevel, number]> = [
    ["low", totals.lowMiles],
    ["moderate", totals.moderateMiles],
    ["high", totals.highMiles],
    ["severe", totals.severeMiles],
    ["no_travel", totals.noTravelMiles],
  ];
  const total = totals.totalMiles || 1;
  return values
    .filter(([, miles]) => miles > 0)
    .map(([level, miles]) => ({
      level,
      miles,
      percent: (miles / total) * 100,
    }));
}

export function riskScore(averageRisk: number): number {
  return Math.round((averageRisk / 4) * 100);
}

export function riskDescriptor(averageRisk: number): RiskLevel {
  if (averageRisk < 0.35) return "low";
  if (averageRisk < 1.1) return "moderate";
  if (averageRisk < 2.15) return "high";
  return "severe";
}

export function riskColor(level: RiskLevel): string {
  return RISK_META[level].color;
}

export function riskLabel(level: RiskLevel): string {
  return RISK_META[level].label;
}

export function riskSummary(totals: RouteTotals): string {
  if (totals.noTravelMiles > 0) {
    return `${totals.noTravelMiles.toFixed(1)} no-travel mi`;
  }
  if (totals.severeMiles > 0) {
    return `${totals.severeMiles.toFixed(1)} severe mi`;
  }
  if (totals.highMiles > 0) {
    return `${totals.highMiles.toFixed(1)} high mi`;
  }
  return "No severe weather exposure";
}
