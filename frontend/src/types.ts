export type RiskLevel = "low" | "moderate" | "high" | "severe" | "no_travel";

export interface Weather {
  windMph: number;
  rainInPerHour: number;
  snowInPerHour: number;
  temperatureF: number | null;
}

export interface RiskAssessment {
  level: RiskLevel;
  label: string;
  reasons: string[];
}

export interface Checkpoint {
  mile: number;
  coveredMiles: number;
  lat: number;
  lon: number;
  eta: string;
  weather: Weather;
  risk: RiskAssessment;
}

export interface RouteTotals {
  lowMiles: number;
  moderateMiles: number;
  highMiles: number;
  severeMiles: number;
  noTravelMiles: number;
  totalMiles: number;
  averageRisk: number;
  maxRisk: RiskLevel;
  maxRiskLabel: string;
}

export interface RouteOption {
  id: string;
  label: string;
  distanceMiles: number;
  durationMinutes: number;
  geometry: [number, number][];
  checkpoints: Checkpoint[];
  totals: RouteTotals;
}

export interface Recommendation {
  routeId: string;
  rationale: string;
  rankedRouteIds: string[];
  recommendedTotals: {
    severeMiles: number;
    highMiles: number;
  };
}

export interface TripPlan {
  planId: string;
  origin: { label: string; lat: number; lon: number };
  destination: { label: string; lat: number; lon: number };
  departure: string;
  loadWeightLb: number;
  samplingIntervalMiles: number;
  generatedAt: string;
  warnings: string[];
  routes: RouteOption[];
  recommendation: Recommendation;
}

export interface PlanRequest {
  origin: string;
  destination: string;
  departure: string;
  loadWeightLb: number;
  samplingIntervalMiles: 10 | 25 | 50;
}

export interface HeatmapPoint {
  lat: number;
  lon: number;
  weather: Weather;
  risk: RiskAssessment;
}

export interface HeatmapFrame {
  planId: string;
  routeId: string;
  hour: number;
  forecastTime: string;
  points: HeatmapPoint[];
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string[]>;
  };
}
