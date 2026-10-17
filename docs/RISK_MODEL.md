# Risk model

This document is the source of truth for the safety rules implemented in `backend/apps/trips/domain/risk.py` and `checkpoints.py`.

## Units

| Quantity | Unit |
| --- | --- |
| Wind | mph |
| Rain | inches per hour |
| Snow | inches per hour |
| Temperature | °F (display only; not used in risk) |
| Distance | miles |
| Load | pounds |
| Time | UTC internally, local time in the UI |

## Weather thresholds

Each condition is classified independently. The checkpoint's base risk is the **worst** of wind, rain, and snow.

| Condition | Low | Moderate | High | Severe | No Travel |
| --- | --- | --- | --- | --- | --- |
| Wind | < 25 mph | 25–34 | 35–44 | 45–54 | ≥ 55 |
| Rain | < 0.10 in/hr | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | > 1.00 |
| Snow | < 0.5 in/hr | 0.5–1.0 | 1.0–2.0 | 2.0–3.0 | > 3.0 |

### Boundary semantics

Continuous values are classified with explicit thresholds. Where the assessment table has overlapping endpoints, the **higher** category wins for safety:

| Value | Result |
| --- | --- |
| Wind `24.999` | Low |
| Wind `25.0` | Moderate |
| Wind `34.999` | Moderate |
| Wind `35.0` | High |
| Wind `44.999` | High |
| Wind `45.0` | Severe |
| Wind `54.999` | Severe |
| Wind `55.0` | No Travel |
| Rain `0.099` | Low |
| Rain `0.10` | Moderate |
| Rain `0.249` | Moderate |
| Rain `0.25` | High |
| Rain `0.499` | High |
| Rain `0.50` | Severe |
| Rain `1.00` | Severe |
| Rain `1.001` | No Travel |
| Snow `0.499` | Low |
| Snow `0.50` | Moderate |
| Snow `0.999` | Moderate |
| Snow `1.0` | High |
| Snow `1.999` | High |
| Snow `2.0` | Severe |
| Snow `3.0` | Severe |
| Snow `3.001` | No Travel |

## Load rules

Load overrides are applied after the base weather classification:

1. Wind ≥ 55 mph → **No Travel** for any load.
2. Wind 45–54 mph and load > 30,000 lb → **No Travel**.
3. Wind 35–44 mph and load > 40,000 lb → **Severe** (raises High to Severe).
4. Load exactly 30,000 lb or 40,000 lb does **not** trigger an override because the rule says "more than".

Examples:

| Wind | Load | Result |
| --- | --- | --- |
| 40 mph | 40,000 lb | High |
| 40 mph | 40,001 lb | Severe |
| 45 mph | 30,000 lb | Severe |
| 45 mph | 30,001 lb | No Travel |
| 55 mph | 0 lb | No Travel |
| 10 mph, rain 1.2 in/hr | 42,000 lb | No Travel (rain) |

The API includes human-readable `risk.reasons` for each checkpoint. When multiple conditions share the worst level, all contributing reasons are included.

## Checkpoint sampling and ETA

- Sampling intervals are **10, 25, or 50 miles**, chosen per request (default 25).
- Checkpoints are placed at the first interval, every interval thereafter, and at the destination. The destination is included even when it is not a multiple of the interval.
- Position is interpolated along the routing step geometry.
- ETA is interpolated using each OSRM step's distance and duration:
  `eta = segment_start + fraction × segment_duration`.
- Checkpoints use the forecast hour that contains the ETA (floor to the hour, UTC).
- Each checkpoint's risk applies to the distance since the previous checkpoint (`coveredMiles`). The first checkpoint covers the first interval; the last may cover a shorter remainder.

## Route totals

For each route:

- `lowMiles`, `moderateMiles`, `highMiles`, `severeMiles`, `noTravelMiles` are the sums of `coveredMiles` for checkpoints at each level.
- `totalMiles` is the sum of covered miles (approximately the route distance).
- `averageRisk` is the mileage-weighted average of the risk scores:
  - Low = 0, Moderate = 1, High = 2, Severe = 3, No Travel = 4.
- `maxRisk` is the highest checkpoint level.

## Recommendation policy

The recommendation is intentionally safety-first:

1. **No Travel gate.** If at least one route has zero No Travel miles, routes with No Travel exposure are excluded from the recommended pool. If every route has No Travel exposure, all routes remain eligible.
2. Fewest **severe miles**.
3. Fewest **high miles**.
4. Lowest **mileage-weighted average risk**.
5. Shortest **travel time**.
6. Stable tie-break by route ID.

For all-No-Travel plans, the ranking additionally uses the fewest No Travel miles before severe/high/average risk. This is the only extension to the assessment's stated order, and it only applies when no safe route exists.

The rationale returned by the API describes the winning metrics and notes when No Travel routes were avoided. The frontend labels an all-No-Travel winner as the "lowest-exposure option" rather than the "safest choice".

## Weather heatmap

- The heatmap is computed for the **selected route**.
- Corridor points are sampled every 10 miles, capped at 16 points to keep the first frame responsive.
- The forecast window is the departure hour plus 0–48 hours.
- A frame's risk is the classification at the selected forecast time, using the same weather + load rules.
- The UI colors each corridor point by risk. The 0–48 hour slider is measured from the departure hour.

## What the model does not do

- It does not model road surface state, visibility, flooding, closures, chain laws, or driver hours.
- It does not use traffic-aware ETAs; OSRM durations are free-flow estimates.
- It samples point forecasts at road coordinates, not a full weather grid.
- It does not replace a dispatcher's judgment. No Travel results should be treated as a hard stop for planning purposes.
