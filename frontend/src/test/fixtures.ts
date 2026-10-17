import type { RouteOption, TripPlan } from "../types";

export const routeFixture: RouteOption = {
  id: "route-1",
  label: "Route 1",
  distanceMiles: 213.5,
  durationMinutes: 281,
  geometry: [
    [40.71, -74.0],
    [41.2, -72.5],
    [42.36, -71.06],
  ],
  checkpoints: [
    {
      mile: 25,
      coveredMiles: 25,
      lat: 40.95,
      lon: -73.75,
      eta: "2026-10-18T16:43:00Z",
      weather: {
        windMph: 3.7,
        rainInPerHour: 0,
        snowInPerHour: 0,
        temperatureF: 50.8,
      },
      risk: { level: "low", label: "Low", reasons: ["Low conditions"] },
    },
    {
      mile: 50,
      coveredMiles: 25,
      lat: 41.2,
      lon: -73.5,
      eta: "2026-10-18T17:26:00Z",
      weather: {
        windMph: 40,
        rainInPerHour: 0.3,
        snowInPerHour: 0,
        temperatureF: 48,
      },
      risk: { level: "high", label: "High", reasons: ["Wind 40 mph is high risk"] },
    },
    {
      mile: 75,
      coveredMiles: 25,
      lat: 41.45,
      lon: -73.2,
      eta: "2026-10-18T18:09:00Z",
      weather: {
        windMph: 50,
        rainInPerHour: 0,
        snowInPerHour: 0,
        temperatureF: 45,
      },
      risk: { level: "no_travel", label: "No Travel", reasons: ["45-54 mph wind with heavy load"] },
    },
    {
      mile: 100,
      coveredMiles: 25,
      lat: 41.7,
      lon: -72.9,
      eta: "2026-10-18T18:52:00Z",
      weather: {
        windMph: 10,
        rainInPerHour: 0,
        snowInPerHour: 0,
        temperatureF: 52,
      },
      risk: { level: "low", label: "Low", reasons: ["Low conditions"] },
    },
  ],
  totals: {
    lowMiles: 50,
    moderateMiles: 0,
    highMiles: 25,
    severeMiles: 0,
    noTravelMiles: 25,
    totalMiles: 100,
    averageRisk: 1.5,
    maxRisk: "no_travel",
    maxRiskLabel: "No Travel",
  },
};

export const planFixture: TripPlan = {
  planId: "6f43f7e5-5b2d-4a3c-b6b3-3f6f9c1e2a10",
  origin: { label: "New York, NY", lat: 40.71, lon: -74.0 },
  destination: { label: "Boston, MA", lat: 42.36, lon: -71.06 },
  departure: "2026-10-18T16:00:00Z",
  loadWeightLb: 42000,
  samplingIntervalMiles: 25,
  generatedAt: "2026-10-17T16:00:00Z",
  warnings: [],
  routes: [
    routeFixture,
    { ...routeFixture, id: "route-2", label: "Route 2", durationMinutes: 300 },
    { ...routeFixture, id: "route-3", label: "Route 3", durationMinutes: 320 },
  ],
  recommendation: {
    routeId: "route-1",
    rationale: "Fewest severe miles, fewest high miles, and the shortest travel time.",
    rankedRouteIds: ["route-1", "route-2", "route-3"],
    recommendedTotals: { severeMiles: 0, highMiles: 25 },
  },
};
