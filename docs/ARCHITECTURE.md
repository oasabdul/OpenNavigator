# Architecture

OpenNavigator is a small full-stack application with a deliberately strict separation between transport, application orchestration, domain rules, and external adapters.

## System context

```text
Browser (React + Leaflet)
        │  JSON over HTTPS
        ▼
nginx ── static SPA
   │
   └── /api/ ──► Gunicorn ──► Django API views
                                  │
                                  ▼
                           Application use cases
                            │              │
                            ▼              ▼
                       Domain rules    Ports (Protocols)
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                       OSRM /           Open-Meteo       PostgreSQL
                       Nominatim        weather          plan snapshots
```

The browser never talks directly to routing, geocoding, or weather services. All provider calls are server-side, rate-limited, and cached.

## Backend layers

```text
backend/apps/trips/
├── domain/            Pure Python. No Django, HTTP, or third-party clients.
│   ├── entities.py    GeoPoint, RouteOption, Weather, Checkpoint, RiskTotals…
│   ├── geo.py         Haversine, interpolation, corridor sampling
│   ├── risk.py        Weather thresholds + load overrides
│   ├── checkpoints.py Checkpoint sampling, ETA interpolation, risk totals
│   └── recommendation.py  Route ranking and rationale
├── application/       Orchestration. Depends on domain + ports only.
│   ├── ports.py       Geocoder, RoutingProvider, WeatherProvider, repository, cache, clock
│   ├── models.py      Commands, results, plan context, heatmap frames
│   ├── plan_trip.py   PlanTripUseCase
│   ├── heatmap.py     HeatmapUseCase
│   └── errors.py      Expected application errors
├── infrastructure/    Adapters for external systems.
│   ├── geocoding.py   Nominatim
│   ├── routing.py     OSRM + detour fallback + route cache
│   ├── weather.py     Open-Meteo batching + hourly series cache
│   ├── repository.py  Django ORM plan repository
│   ├── cache.py       Django cache adapter
│   └── clock.py       System clock
└── interface/         Django/DRF HTTP boundary.
    ├── views.py       JSON endpoints and error mapping
    ├── serializers.py Request validation
    ├── presenters.py  Domain → camelCase JSON
    ├── container.py   Dependency wiring
    └── exceptions.py  Consistent API error envelope
```

### Dependency rule

`domain` imports nothing from the other layers. `application` imports `domain` and defines ports as `typing.Protocol`. `infrastructure` implements those ports. `interface` wires the use cases and maps errors to HTTP. This keeps risk and ranking rules testable without Django, network access, or a database.

### Why these choices

- **Django + DRF** gives a well-understood HTTP boundary, validation, throttling, ORM, and deployment story without a large framework surface.
- **React + Leaflet** keeps the map layer small and predictable. A canvas heatmap layer avoids one DOM node per gradient, keeping slider updates smooth.
- **PostgreSQL plan snapshots** make heatmap requests independent of process memory and survive restarts. Plans expire after 24 hours.
- **File cache** stores geocodes, route responses, hourly weather series, and heatmap datasets. The server has only ~1 GB RAM, so an in-process cache is not shared across restarts and Redis would add operational weight.
- **No user accounts** are needed for the assessment. The API is anonymous and rate-limited per IP.

## Request lifecycle: plan a trip

1. `PlanTripView` validates the JSON body with a DRF serializer.
2. `PlanTripUseCase` checks the departure window and geocodes both endpoints.
3. `OsrmRouter` requests up to three alternatives. If OSRM returns fewer, the adapter generates perpendicular via-point detours and deduplicates by geometry.
4. For each route, `build_checkpoint_samples` walks routing steps, interpolating position and ETA at every 10/25/50 miles.
5. Checkpoints are grouped into six-hour UTC buckets. `OpenMeteoWeather` fetches each bucket's points in batches, caches each point series, and the use case reads the forecast hour covering each ETA.
6. `assess_weather` classifies each checkpoint; `analyze_route` builds mileage-weighted risk totals.
7. `recommend_routes` ranks safe routes and builds a rationale.
8. `DjangoPlanRepository` stores a compact route snapshot (geometry, departure, load, interval) for later heatmap frames.
9. The presenter serialises geometry, checkpoints, totals, recommendation, and warnings to camelCase JSON.

## Request lifecycle: corridor heatmap

1. `HeatmapView` validates `route_id` and `hour` (0–48).
2. `HeatmapUseCase` loads the plan snapshot from PostgreSQL.
3. On the first frame for a route, it samples the route geometry every 10 miles (up to 16 points), requests a 49-hour forecast for all points, and precomputes 49 frames. The dataset is cached for an hour.
4. Subsequent slider frames are served from the cached dataset, so the UI does not re-hit Open-Meteo while dragging.
5. The React canvas layer draws radial gradients at each corridor point using the risk color for the selected hour.

## Data model

```text
trip_plans
├── id            uuid, primary key
├── created_at    timestamptz
├── expires_at    timestamptz, indexed
└── context       jsonb
    ├── origin / destination
    ├── departure / load / interval
    └── routes[]: id, label, distance, duration, geometry
```

Only the data needed for heatmap recomputation is stored. Checkpoint and recommendation results are returned directly from the plan request.

## External providers and caching

| Provider | Purpose | Cache | Failure behaviour |
| --- | --- | --- | --- |
| Nominatim | Geocode free text | 24 h | `502 upstream_unavailable` |
| OSRM | Driving routes and steps | 30 min | `502 upstream_unavailable`; no route → `422` |
| Open-Meteo | Hourly wind/rain/snow/temp | 15 min per point/window | `502 upstream_unavailable` |
| PostgreSQL | Plan snapshots | 24 h retention | Request fails with a generic 500 |

Requests use a descriptive `User-Agent`; Nominatim calls are rate-limited to one per second. Weather requests are batched (40 coordinates) and parallelised with a bounded thread pool. Routing requests retry once with backoff.

## Frontend structure

```text
frontend/src/
├── api/client.ts        Typed fetch wrapper and API errors
├── hooks/               Planner and heatmap state machines
├── lib/                 Formatting, risk metadata, geometry slicing
├── components/          Form, route cards, checkpoint table, heatmap controls, dialogs
├── features/map/        Leaflet map and canvas weather heatmap layer
├── types.ts             API contract types
└── styles.css           Design tokens and responsive layout
```

The map is imperative Leaflet inside a React lifecycle. Route geometry is split into risk-colored polylines by checkpoint mileage; the weather layer is a custom canvas layer in a dedicated pane below route lines and markers. The heatmap layer redraws only on frame/pan/zoom changes.

## Error handling

- Expected application errors map to a stable envelope: `{"error": {"code", "message"}}`.
- Validation errors include a `fields` object.
- Unexpected exceptions are logged with a stack trace and return `internal_error` without leaking internals.
- The client shows an inline banner with the provider message and keeps the previous plan on screen.

## Testing strategy

- Domain tests are pure and exhaustive around threshold boundaries and load overrides.
- Application tests use fake geocoder/router/weather/repository/clock to verify orchestration and ETA selection.
- Adapter tests use fake HTTP responses to verify parsing, batching, retries, and caching.
- API tests patch the container builders and verify status codes, field names, and persistence.
- Frontend tests cover formatting, geometry slicing, risk presentation, form validation, route cards, and heatmap controls.
- CI runs backend lint/tests and frontend typecheck/tests/build on every push.
