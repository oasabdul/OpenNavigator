# Assumptions and limits

These are the deliberate interpretations behind the assessment implementation.

## Trip and sampling

- **Sampling interval is a choice.** The user selects 10, 25, or 50 miles; the default is 25. The app does not sample all three at once.
- **Checkpoints include the destination.** If the route distance is not a multiple of the interval, the final checkpoint is shorter than the interval.
- **A checkpoint's risk covers the distance since the previous checkpoint.** This makes risk miles sum to the route distance and avoids double-counting.
- **ETA comes from OSRM step durations**, interpolated by distance within each step. It is a free-flow estimate, not a traffic-aware ETA.
- **Departures are limited to 14 days ahead**, matching the practical Open-Meteo forecast horizon. Past departures are rejected with a small five-minute clock-skew tolerance.
- **Origin and destination must be at least 0.25 miles apart.**

## Weather

- Weather is an **hourly point forecast** at the road coordinate. Checkpoints use the forecast hour that contains the ETA (floor to the hour, UTC).
- The heatmap slider is measured **from the departure hour**, not from each point's ETA. This is the standard "forecast at time T" interpretation and keeps the 49 frames consistent.
- Open-Meteo values are requested in mph, °F, and inches. Snowfall is requested with `precipitation_unit=inch` and displayed as in/hr.
- Temperature is displayed in popups but is **not** part of the risk rules.
- Missing hourly values are treated as zero for wind/rain/snow. In practice Open-Meteo returns complete series; the adapter rejects structurally incomplete payloads.

## Risk and recommendation

- **Boundary values roll up to the higher category** where the assessment table overlaps (for example, rain 0.25 in/hr is High, not Moderate). This is documented in [RISK_MODEL.md](RISK_MODEL.md).
- The base weather risk is the **worst** of wind, rain, and snow.
- Load overrides apply only to wind, exactly as specified.
- **No Travel is treated as a safety gate.** If any route has zero No Travel miles, routes with No Travel exposure are excluded from the recommended pool. If every route has No Travel exposure, all remain eligible and the route with the least No Travel mileage is preferred. This is an extension to the assessment's stated ranking and is only used when no safe route exists.
- Average risk is **mileage-weighted** (0–4 scale). The UI also shows a 0–100 score for readability.
- The recommendation is deterministic; route ID is the final tie-break.

## Routing and geocoding

- OSRM's public demo server is used for driving routes. It may return fewer than three alternatives; the adapter adds via-point detours and deduplicates by geometry. If the corridor still cannot produce three distinct routes, the API returns the available routes with a warning.
- Nominatim is used for free-text geocoding with a descriptive User-Agent, a 24-hour cache, and a one-request-per-second limit. `lat, lon` input bypasses the geocoder.
- Units and thresholds are US-centric (mph, inches, pounds). The geocoder is not restricted to the US, but the assessment rules are.
- There is no traffic, road closure, bridge height, hazmat, or hours-of-service routing.

## Heatmap

- The heatmap is for the **selected route**, not all three at once.
- Corridor points are spaced at 10 miles, capped at 16 points for responsiveness. Long routes therefore have coarser heatmap spacing than short routes.
- The first frame for a route builds and caches 49 hourly frames. Subsequent slider frames are served from cache.
- Plans expire after 24 hours; an expired plan returns `410 plan_not_found` and the UI asks the user to plan again.

## Data and operations

- There are no user accounts, saved trips, or personal data. Plan snapshots contain only endpoints, departure, load, interval, and route geometry.
- The public API is anonymous and rate-limited to 60 requests/minute per IP.
- Production uses PostgreSQL for plan snapshots and Django's file cache for provider data. The server has ~1 GB RAM, so the app runs one Gunicorn worker with four threads and no on-server frontend builds.
- Free external services can be slow or rate-limited. The app shows provider errors, retries routing/weather once, and keeps the previous plan visible on a failed replan.
