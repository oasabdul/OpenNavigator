# Loom walkthrough script

Target length: **7–9 minutes**. The assessment asks for 5–10 minutes.

Before recording:

```bash
# Terminal 1
cd backend && ../.venv/bin/python manage.py runserver 127.0.0.1:8000

# Terminal 2
cd frontend && pnpm dev
```

Open <http://localhost:5173> at a 1440-wide window. Have the hosted URL ready as a backup.

## 0:00 — Intro (30 s)

> "This is OpenNavigator, a weather-aware truck routing app built with React and Django. A dispatcher enters an origin, destination, departure time, and load weight. The app builds three real road routes, samples the forecast at the truck's estimated arrival time, applies the assessment's weather and load rules, and recommends the safest route."

Show the empty planner and the muted map.

## 0:30 — Plan a trip (60 s)

- Origin: `New York, NY`
- Destination: `Boston, MA`
- Leave the departure at the default future time.
- Set load to **42,000 lb**.
- Leave sampling at **25 mi**.
- Click **Plan safest route**.

While loading, point out the staged status: locating places, building routes, sampling weather, scoring risk.

> "Routing and geocoding happen server-side. Weather is fetched in six-hour buckets and read at each checkpoint's ETA, so a 25-mile checkpoint at 4:43 PM uses the 4 PM forecast hour."

## 1:30 — Recommendation and route summaries (90 s)

When results arrive:

- Point out the recommendation banner and rationale.
- Highlight the **Recommended** and **Fastest** badges.
- Read the risk bar and the Severe/High/Avg risk stats.
- Select another route and show the map focusing on it; then reselect the recommended route.
- Mention that No Travel routes are deprioritized when a safer route exists.

> "The ranking is safety-first: no-travel exposure first, then severe miles, high miles, mileage-weighted average risk, and travel time. The rationale is generated from the same numbers."

## 3:00 — Map and checkpoint log (90 s)

- Zoom into the route.
- Click a checkpoint marker; show ETA, wind, rain, snow, risk, and reason.
- Show the **Checkpoint log** in the sidebar; scroll a few rows.
- Point out origin/destination markers and the risk-colored route segments.

> "Every checkpoint is tied to a mile marker, an ETA, and a weather observation. The route line is split by the risk at each checkpoint."

## 4:30 — 48-hour corridor heatmap (90 s)

- The heatmap is on by default for the selected route.
- Drag the slider from +0h to +24h to +48h.
- Press play and let it animate.
- Point out that the colors are the same risk scale and that the first frame builds the corridor dataset server-side; subsequent frames are cached.

> "The heatmap samples the selected route every 10 miles and precomputes 49 hourly frames. The slider is measured from the departure hour. This keeps dragging smooth and avoids hammering the weather API."

## 6:00 — Risk model and edge cases (60 s)

- Click **Risk model** in the header.
- Show the threshold table, boundary note, load rules, and recommendation order.
- Mention the tests around boundaries and load overrides.
- Optional: close the dialog, change load to 80,000 lb and replan to show load-sensitive results. Or run `Chicago → Denver` at 10-mile sampling to show a longer route.

> "Boundary values roll up to the higher risk category for safety. Load overrides only apply to wind: 45–54 mph with more than 30,000 lb is No Travel, and 35–44 mph with more than 40,000 lb is Severe."

## 7:00 — Architecture and code quality (60 s)

Open the repo in an editor:

- `backend/apps/trips/domain/risk.py` — pure rules.
- `backend/apps/trips/domain/checkpoints.py` — sampling/ETA interpolation.
- `backend/apps/trips/domain/recommendation.py` — ranking.
- `backend/apps/trips/application/plan_trip.py` — orchestration with ports.
- `backend/apps/trips/infrastructure/` — OSRM, Nominatim, Open-Meteo adapters.
- `frontend/src/features/map/` — Leaflet map and canvas heatmap layer.

> "The domain has no Django or HTTP imports. The use case depends on protocols, so the tests use fake providers. The infrastructure adapters are replaceable."

Show the test commands:

```bash
make test
make lint
```

> "97 backend tests and 21 frontend tests. CI runs lint, tests, typecheck, and the production build."

## 8:30 — Deployment and close (30 s)

Show the hosted URL and the health endpoint.

> "The app is deployed to a dedicated system user and database on the shared server, behind nginx and Let's Encrypt. Frontend builds happen locally and only artifacts are shipped because the server has about 1 GB of RAM. Backups run daily via a systemd timer."

Close:

> "OpenNavigator prioritizes correctness and clarity: the risk model is isolated and tested, the recommendation is explainable, and the map makes the weather exposure visible along the route."

## Backup talking points

- Free stack: OSRM, Nominatim, Open-Meteo; no paid keys.
- Plan snapshots are stored in PostgreSQL for heatmap requests and expire after 24 hours.
- Weather and route responses are cached; Nominatim is rate-limited.
- The API returns a consistent error envelope and the UI keeps the previous plan on a failed replan.
- Mobile layout puts the map between the planner and the route results.
