# API reference

Base path: `/api/v1`

All responses are JSON. Timestamps are ISO 8601 UTC. Distances are miles, speed is mph, precipitation is inches per hour, temperature is °F, and load is pounds.

## Health

`GET /health/`

```json
{
  "status": "ok",
  "service": "OpenNavigator API",
  "version": "1.0.0",
  "time": "2026-10-17T17:43:32.299783+00:00"
}
```

## Config

`GET /config/`

Returns the sampling options, forecast horizon, units, and risk labels used by the UI.

```json
{
  "samplingIntervalsMiles": [10, 25, 50],
  "forecastHours": 48,
  "units": { "distance": "miles", "wind": "mph", "precipitation": "in/hr" },
  "riskLevels": [
    { "key": "low", "label": "Low" },
    { "key": "moderate", "label": "Moderate" },
    { "key": "high", "label": "High" },
    { "key": "severe", "label": "Severe" },
    { "key": "no_travel", "label": "No Travel" }
  ]
}
```

## Plan a trip

`POST /trips/plan/`

### Request

```json
{
  "origin": "New York, NY",
  "destination": "Boston, MA",
  "departure": "2026-10-18T16:00:00Z",
  "load_weight_lb": 42000,
  "sampling_interval_miles": 25
}
```

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `origin` | string | yes | 2–240 chars; city, address, or `lat, lon` |
| `destination` | string | yes | 2–240 chars; city, address, or `lat, lon` |
| `departure` | ISO datetime | yes | Must include a timezone; not in the past; up to 14 days ahead |
| `load_weight_lb` | number | yes | 0–200,000 |
| `sampling_interval_miles` | integer | no | `10`, `25` (default), or `50` |

### Response `200 OK`

The response is abbreviated below. A real plan contains 3 routes and all checkpoints.

```json
{
  "planId": "0b8a582b-80f7-4c82-98a3-f5bf97b52031",
  "origin": {
    "label": "New York, New York, United States",
    "lat": 40.712118,
    "lon": -74.005737
  },
  "destination": {
    "label": "Boston, Massachusetts, United States",
    "lat": 42.358833,
    "lon": -71.05783
  },
  "departure": "2026-10-18T16:00:00+00:00",
  "loadWeightLb": 42000,
  "samplingIntervalMiles": 25,
  "generatedAt": "2026-10-17T17:45:18.000000+00:00",
  "warnings": [],
  "routes": [
    {
      "id": "route-1",
      "label": "Route 1",
      "distanceMiles": 213.5,
      "durationMinutes": 280.6,
      "geometry": [[40.71212, -74.00574], [40.9463, -73.74903], [42.35883, -71.05783]],
      "checkpoints": [
        {
          "mile": 25.0,
          "coveredMiles": 25.0,
          "lat": 40.9463,
          "lon": -73.74903,
          "eta": "2026-10-18T16:43:31.516877+00:00",
          "weather": {
            "windMph": 3.7,
            "rainInPerHour": 0.0,
            "snowInPerHour": 0.0,
            "temperatureF": 50.8
          },
          "risk": {
            "level": "low",
            "label": "Low",
            "reasons": ["Wind, rain, and snow are within low-risk thresholds"]
          }
        }
      ],
      "totals": {
        "lowMiles": 213.5,
        "moderateMiles": 0.0,
        "highMiles": 0.0,
        "severeMiles": 0.0,
        "noTravelMiles": 0.0,
        "totalMiles": 213.5,
        "averageRisk": 0.0,
        "maxRisk": "low",
        "maxRiskLabel": "Low"
      }
    }
  ],
  "recommendation": {
    "routeId": "route-1",
    "rationale": "Fewest severe miles (0.0), fewest high miles (0.0), lowest average risk (0.00), with travel time as the final tie-breaker (281 min) among the options without No-travel conditions.",
    "rankedRouteIds": ["route-1", "route-2", "route-3"],
    "recommendedTotals": { "severeMiles": 0.0, "highMiles": 0.0 }
  }
}
```

#### Route fields

| Field | Meaning |
| --- | --- |
| `geometry` | Thinned `[lat, lon]` polyline for map rendering (up to ~800 points) |
| `checkpoints` | One sample per interval plus the destination |
| `checkpoint.mile` | Distance from origin at the checkpoint |
| `checkpoint.coveredMiles` | Distance attributed to this checkpoint's risk (interval length, last segment may be shorter) |
| `checkpoint.eta` | Estimated arrival time from OSRM step durations |
| `totals.*Miles` | Miles attributed to each risk level |
| `totals.averageRisk` | Mileage-weighted average risk on a 0–4 scale |
| `totals.maxRisk` | Highest risk level on the route |

#### Recommendation fields

| Field | Meaning |
| --- | --- |
| `routeId` | Recommended route |
| `rationale` | Human-readable explanation |
| `rankedRouteIds` | Full ranking, safest first |
| `recommendedTotals` | Severe/high miles for the winner |

### Errors

| HTTP | `error.code` | When |
| --- | --- | --- |
| 400 | `validation_error` | Missing/invalid fields; includes `fields` |
| 400 | `invalid_trip` | Past departure, horizon exceeded, same endpoints, invalid interval/load |
| 422 | `location_not_found` | Geocoder found no match |
| 422 | `route_not_found` | No drivable route |
| 502 | `upstream_unavailable` | Routing, geocoding, or weather provider failed |
| 429 | `request_error` | Anonymous rate limit exceeded |
| 500 | `internal_error` | Unexpected server failure |

Error envelope:

```json
{
  "error": {
    "code": "location_not_found",
    "message": "No location found for 'Atlantis'"
  }
}
```

Validation errors also include `error.fields`, e.g. `{"departure": ["This field is required."]}`.

## Corridor heatmap

`GET /trips/{plan_id}/heatmap/?route_id=route-1&hour=12`

| Query | Type | Rules |
| --- | --- | --- |
| `route_id` | string | Must exist in the plan |
| `hour` | integer | 0–48 hours from the departure hour |

### Response `200 OK`

```json
{
  "planId": "0b8a582b-80f7-4c82-98a3-f5bf97b52031",
  "routeId": "route-1",
  "hour": 12,
  "forecastTime": "2026-10-19T04:00:00+00:00",
  "points": [
    {
      "lat": 40.71212,
      "lon": -74.00574,
      "weather": {
        "windMph": 4.0,
        "rainInPerHour": 0.0,
        "snowInPerHour": 0.0,
        "temperatureF": 43.0
      },
      "risk": {
        "level": "low",
        "label": "Low",
        "reasons": ["Wind, rain, and snow are within low-risk thresholds"]
      }
    }
  ]
}
```

The first request for a route builds and caches 49 hourly frames; subsequent slider requests are fast. Plans expire after 24 hours.

### Errors

| HTTP | `error.code` | When |
| --- | --- | --- |
| 400 | `validation_error` | Invalid `route_id`/`hour` query |
| 400 | `invalid_forecast_hour` | Hour outside 0–48 |
| 410 | `plan_not_found` | Plan expired or route not in plan |
| 502 | `upstream_unavailable` | Weather provider failed |
| 500 | `internal_error` | Unexpected server failure |

## Rate limits

Anonymous clients are limited to 60 requests per minute per IP. Health and config endpoints are exempt.

## Provider notes

- OSRM demo server: public, no SLA, alternatives may be fewer than three; the adapter adds detours.
- Nominatim: one request per second per process, 24-hour cache, descriptive User-Agent.
- Open-Meteo: hourly forecast, cached for 15 minutes per point/window.
