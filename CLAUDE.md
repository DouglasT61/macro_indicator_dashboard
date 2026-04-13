# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Macro Stress Dashboard** is a local FastAPI + React application that tracks the macro stress chain from marine insurance disruption and oil scarcity into dollar funding stress, Treasury market dysfunction, Fed backstops, and medium-term repression risk.

The app runs with live public feeds (FRED, EIA, AIS Hub, market data) where available and degrades gracefully when feeds fail. A regime engine evaluates stress propagation through causal chains, generating regime scores (Sticky/Convex/Break) and alerts. The frontend visualizes indicators, regime state, causal chains, crisis signals, and state-space forecasts.

**Tech Stack:**
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0, APScheduler, Pydantic V2
- Frontend: React 18, TypeScript, Vite, ECharts, react-markdown
- Database: SQLite (local), Postgres (production)
- Deployment: Docker Compose (local), DigitalOcean App Platform (cloud)

## Commands

### Backend

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run backend dev server (port 8005)
cd backend && python -m uvicorn app.main:app --reload --port 8005

# Run all backend tests
python -m pytest tests/backend -q
python -m pytest tests/backend -v        # Verbose

# Run specific test file
python -m pytest tests/backend/test_regime_engine.py -v

# Run specific test
python -m pytest tests/backend/test_regime_engine.py::test_regime_scoring -v
```

### Frontend

```bash
# Install dependencies
cd frontend && npm install

# Run dev server (port 5173, proxies /api to backend)
cd frontend && npm run dev

# Build for production
cd frontend && npm run build

# Preview production build
cd frontend && npm run preview

# TypeScript type check
cd frontend && npx tsc --noEmit
```

### Docker (Recommended)

```bash
# Start both services (backend on 8005, frontend on 4173)
docker compose up --build

# Stop services
docker compose down

# Full reset (deletes persistent volumes)
docker compose down -v

# View backend logs
docker compose logs backend -f

# View frontend logs
docker compose logs frontend -f
```

### Database

SQLite is used locally (auto-created on first run in `backend/data/` or volume). In production, Postgres is recommended. No migrations are needed — SQLAlchemy creates tables on app startup via `Base.metadata.create_all()`.

## Architecture

### High-Level Data Flow

1. **Collectors** (in `backend/app/collectors/`) fetch data from external sources:
   - `public_data.py` → FRED API (Federal Reserve Economic Data), EIA API
   - `public_shipping.py` → AIS Hub ship position data
   - `marine_insurance_collector.py` → Marine insurance indices
   - `demo_collector.py` → Deterministic baseline data
   - All collectors gracefully degrade on network failure

2. **Data Storage**: Collectors write `IndicatorValue` records to the database, timestamped and unique per series per timestamp.

3. **Regime Engine** (`backend/app/regime_engine/engine.py`):
   - Reads regime configuration from `backend/config/regime_config.json`
   - Evaluates indicator thresholds and normalizes values
   - Builds base node scores from causal groups
   - Propagates stress through a directed acyclic graph of nodes (Oil/Shipping → Funding → UST → Asset Regime, etc.)
   - Applies feedback loops and amplification with configurable activation floors, memory, and feedback gains
   - Generates three regime scores: Sticky (tendency to stay in regime), Convex (curvature risk), Break (tail risk)

4. **Alerts** (`backend/app/alerts/engine.py`):
   - Rules-based alert engine triggered by regime transitions, high scores, or indicator extremes
   - Stores `Alert` records with severity, title, body, related indicators, and next-stage consequence

5. **Dashboard Service** (`backend/app/services/dashboard_service.py`):
   - Aggregates current indicator state, regime scores, alerts, manual overlays, and event annotations
   - Returns `DashboardOverview` schema for frontend consumption

6. **Frontend** (`frontend/src/`):
   - React components render indicators, regime cards, causal chain DAG, crisis monitor, and state-space forecast panels
   - Fetch API calls to backend for data; localStorage caches state

### Key Tables

- **IndicatorSeries**: Metadata (name, category, source, frequency, unit, description)
- **IndicatorValue**: Timestamped values with computed fields (normalized_value, zscore, moving_average_7/30, percentile, rate_of_change, acceleration)
- **RegimeScore**: Timestamped Sticky/Convex/Break scores with JSON explanation
- **Alert**: Timestamped crisis signals with related indicators and consequence forecasts
- **ManualInput**: User overlays (e.g., custom recession flags or stress adjustments)
- **AppSetting**: Key-value JSON blobs (e.g., alert settings, display preferences)
- **EventAnnotation**: User-created event markers (e.g., "FOMC meeting", "geopolitical shock")

### Configuration

**Environment variables** (`backend/.env` or Docker Compose):
- `APP_ENV`: "development" or "docker"
- `API_HOST`, `API_PORT`: FastAPI server binding
- `FRONTEND_ORIGIN`: CORS origin for frontend
- `DATABASE_URL`: SQLite (`sqlite:///path`) or Postgres (`postgresql+psycopg://...`)
- `DEMO_MODE`: Whether to seed deterministic baseline data
- `SCHEDULER_ENABLED`: Whether APScheduler starts on app initialization
- `BOOTSTRAP_ON_STARTUP`: Whether to seed initial data
- `REFRESH_HOUR`, `REFRESH_MINUTE`: Daily scheduled refresh time
- `ENABLE_ALERTS`: Whether alert engine runs
- `REGIME_CONFIG_PATH`: Path to regime configuration JSON
- `FRED_API_KEY`, `EIA_API_KEY`, `MARKET_DATA_API_KEY`, `AISHUB_USERNAME`: Optional API credentials

**Regime Configuration** (`backend/config/regime_config.json`):
- `thresholds`: Per-indicator min/max for normalization (0–100 scale)
- `regime_weights`: Weighted contribution of nodes to regime scores
- `alert_rules`: Rules for triggering alerts
- `causal_groups`: Mapping of nodes to their constituent indicators
- `propagation`: Parameters for stress propagation (activation_floor, memory, feedback_gain, max_node_boost, iterations, edges)

### API Endpoints

- `GET /api/v1/health` → `{"status": "ok"}`
- `GET /api/v1/dashboard/overview` → `DashboardOverview` (all current state)
- `POST /api/v1/dashboard/refresh` → Trigger async data refresh
- `GET /api/v1/dashboard/export/daily-summary` → Markdown export of current state
- `GET /api/v1/settings` / `POST /api/v1/settings` → User preferences (display, alerts)

### Key Patterns

**Services Pattern**: Business logic lives in `backend/app/services/`. Each service is stateless and accepts a database session. Example:
```python
# dashboard_service.get_dashboard_overview(db)
# refresh_service.run_refresh_in_new_session()
# state_space_service.forecast_stochastic(db, ...)
```

**Collector Pattern**: Each collector is a function that fetches external data and writes `IndicatorValue` records. They catch exceptions and log gracefully to avoid blocking the refresh.

**SQLAlchemy 2.0**: All models use `Mapped[T]` type hints with `mapped_column()`. Sessions use `expire_on_commit=False` to keep loaded objects live after commit.

**Pydantic V2**: Serialization via `model_validate()` and `model_dump()`. Float/Decimal handling is strict — always validate input from API payloads.

**Graceful Degradation**: Collectors are wrapped in try-except; missing feeds don't crash the app. Demo mode provides a bootstrap baseline if all feeds fail.

**Async Refresh**: Long-running data collection happens in background via `BackgroundTasks`. A lock (`refresh_queued_flag`) prevents overlapping refreshes.

## Testing

**Backend tests** (`tests/backend/`) use pytest with fixtures in `tests/conftest.py`:

```bash
# Run all backend tests
python -m pytest tests/backend -v

# Run specific test module
python -m pytest tests/backend/test_regime_engine.py -v

# Run test with coverage
python -m pytest tests/backend --cov=app --cov-report=html
```

Test modules:
- `test_regime_engine.py`: Regime scoring, propagation, causal chains
- `test_alert_engine.py`: Alert triggering rules and severity logic
- `test_api_routes.py`: Endpoint responses and error handling
- `test_*_collector.py`: Data fetching and graceful degradation
- `test_state_space_*.py`: State-space calibration, forecast, sensitivity

**Frontend**: No test suite in this repo. E2E testing via browser.

## Important Gotchas

1. **APScheduler in Docker**: Only one backend instance should run; scheduler is not distributed. In production (DigitalOcean App Platform), deploy a single backend service and autoscaling frontend.

2. **Nullable Fields**: Many indicator values are nullable (missing data, API failures). Services must handle `None` gracefully.

3. **Regime Config Reload**: Changes to `regime_config.json` require app restart. No hot-reload.

4. **Demo Mode**: When `DEMO_MODE=true`, the app seeds a deterministic bootstrap baseline. Turn off in production to avoid stale seeded data.

5. **CORS Origins**: Frontend dev ports (5173, 5174) and Docker port (4173) are whitelisted in `app.main.py`. Add custom domains to `allowed_origins` list if needed.

6. **Database Migrations**: SQLAlchemy handles schema auto-creation. No Alembic migration tooling is in use.

7. **Floating Point**: Stress propagation uses floats. Be aware of rounding artifacts in regime scores at extreme values.

## Deployment

### Local Docker (Recommended)
```bash
docker compose up --build
```
Mounts volumes `macro_dashboard_data` and `macro_dashboard_exports` for persistence.

### DigitalOcean App Platform
1. Push repo to GitHub
2. In App Platform, create app from `.do/app.yaml` spec
3. Set environment secrets: `FRED_API_KEY`, `EIA_API_KEY`, `MARKET_DATA_API_KEY`, `AISHUB_USERNAME`
4. Use Postgres for database (set `DATABASE_URL` in environment)
5. Scale frontend horizontally; keep backend at 1 instance for APScheduler

### Environment Notes
- **SQLite** is not suitable for multi-instance deployment (locking issues)
- **Postgres** is recommended for cloud (auto-managed on App Platform)
- Refresh can take 30+ seconds if external feeds are slow; refresh timeout is configurable via `BackgroundTasks` integration

## Common Development Tasks

**Add a new indicator series**:
1. Create a collector function in `backend/app/collectors/` that fetches data and yields `(key, name, value, timestamp)` tuples
2. Register in the seed catalog (`backend/app/seed/catalog.py`)
3. Add thresholds and causal group mapping to `backend/config/regime_config.json`
4. Add to UI panel component in `frontend/src/components/`

**Modify regime rules**:
1. Edit `backend/config/regime_config.json`: thresholds, weights, propagation parameters, alert rules
2. Test via `pytest tests/backend/test_regime_engine.py`
3. Restart app to reload config

**Export daily summary**:
- Frontend can call `GET /api/v1/dashboard/export/daily-summary`
- Returns Markdown with current state, alerts, regime scores, key indicators
- Suitable for embedding in daily reports or email digests

**Check live data feed status**:
1. Backend logs (Docker: `docker compose logs backend -f`) show collector success/failure
2. If a feed fails, demo mode bootstraps a baseline and the app continues
3. Next scheduled refresh will re-attempt all feeds

## File Structure Reference

```
backend/
  app/
    main.py                   # FastAPI app initialization, CORS, lifespan
    core/
      config.py              # Settings from environment
      database.py            # SQLAlchemy engine, session factory
      scheduler.py           # APScheduler initialization
    models/
      models.py              # SQLAlchemy ORM models
    api/
      router.py              # API router aggregation
      endpoints/
        dashboard.py         # /dashboard endpoints
        health.py            # /health endpoint
        settings.py          # /settings endpoints
    services/                # Business logic
      dashboard_service.py
      refresh_service.py
      state_space_service.py
      analytics.py
      ... (more services)
    regime_engine/
      engine.py              # Regime scoring + propagation
      config_loader.py       # Load regime_config.json
    alerts/
      engine.py              # Alert triggering
    collectors/              # External data fetchers
      public_data.py
      public_shipping.py
      marine_insurance.py
      ... (more collectors)
    seed/
      catalog.py             # Indicator metadata catalog
  config/
    regime_config.json       # Regime thresholds, weights, rules
  requirements.txt           # Python dependencies
frontend/
  src/
    App.tsx                  # Root component
    main.tsx                 # ReactDOM mount
    pages/
      DashboardPage.tsx      # Main dashboard layout
    components/              # Reusable React components
      SummaryCard.tsx        # Regime cards
      CausalChain.tsx        # Causal chain DAG
      IndicatorTile.tsx      # Indicator display
      CrisisMonitor.tsx      # Crisis alerts
      ... (more components)
    charts/                  # ECharts wrappers
      LineChart.tsx
      SparklineChart.tsx
  package.json
  tsconfig.json
  vite.config.ts
tests/
  backend/
    test_regime_engine.py
    test_alert_engine.py
    ... (more tests)
  conftest.py                # Shared pytest fixtures
docker-compose.yml           # Local Docker setup
Dockerfile.backend
Dockerfile.frontend
.env.example
.do/
  app.yaml                   # DigitalOcean App Platform spec
.github/
  workflows/
    ci.yml                   # GitHub Actions CI
```
