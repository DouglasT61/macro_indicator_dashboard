# Macro Stress Dashboard

A local FastAPI + React application that tracks the macro stress chain from marine insurance disruption and oil scarcity into dollar funding stress, Treasury market dysfunction, Fed backstops, and medium-term repression risk.

## Recommended Cloud Deployment

The recommended public deployment path is:

1. put the codebase in GitHub
2. deploy from GitHub to DigitalOcean App Platform
3. use DigitalOcean's public app URL
4. run the backend against managed Postgres, not SQLite

This is the recommended path because:

- App Platform can redeploy automatically from GitHub on push.
- App Platform publishes the app on a public DigitalOcean URL without requiring a custom domain first.
- GitHub supports pushing an existing local project to a new repository with standard Git commands.

Deployment artifacts included in this repo:

- [D:\Data\OneDrive\Desktop\macro_indicator_dashboard\.do\app.yaml](D:/Data/OneDrive/Desktop/macro_indicator_dashboard/.do/app.yaml)
- [D:\Data\OneDrive\Desktop\macro_indicator_dashboard\.github\workflows\ci.yml](D:/Data/OneDrive/Desktop/macro_indicator_dashboard/.github/workflows/ci.yml)

## What the App Does

The dashboard is built around one thesis: a marine-insurance-driven oil shock can propagate into higher energy import bills, global dollar funding stress, weaker foreign marginal demand for U.S. Treasuries, repo and basis-trade stress, Fed plumbing intervention, and eventually inflation / repression risk.

The app runs with live public feeds where available and degrades gracefully when those feeds fail. Docker is the recommended way to share it with other users because it avoids local Python/Node setup and preserves the SQLite database in Docker-managed volumes.

## Stack

- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite, APScheduler
- Frontend: React, TypeScript, Vite, static production build served by Nginx
- Persistence: SQLite in a Docker volume
- Runtime: Docker Compose with two services

## Repository Layout

- `backend/` FastAPI app, regime engine, alerts, seed logic, scheduler
- `frontend/` React dashboard
- `config/` sample local configuration
- `docs/` user guide and exported summary docs
- `scripts/` helper PowerShell scripts for non-Docker local runs
- `tests/` unit tests for regime logic and alerts

## Docker Quick Start

### Prerequisites

- Docker Desktop on Windows or macOS

### Start the app

```bash
docker compose up --build
```

Open:

- Frontend: [http://localhost:4173](http://localhost:4173)
- Backend health: [http://localhost:8005/api/v1/health](http://localhost:8005/api/v1/health)
- Dashboard API: [http://localhost:8005/api/v1/dashboard/overview](http://localhost:8005/api/v1/dashboard/overview)

### What happens on first run

- the backend creates the SQLite schema automatically
- the app seeds a deterministic baseline automatically
- the app queues a live refresh automatically after startup
- APScheduler remains active inside the backend container for scheduled refreshes

### Persistence

Docker Compose creates two named volumes:

- `macro_dashboard_data`
  - SQLite database and app state
- `macro_dashboard_exports`
  - reserved for export/output persistence

These volumes survive container restarts and recreations.

### Stop the app

```bash
docker compose down
```

### Full reset

This removes containers and persistent volumes:

```bash
docker compose down -v
```

## Environment

The Docker setup works with the built-in defaults. Optional environment variables can be provided through shell environment or a root `.env` file.

Useful variables:

- `FRED_API_KEY`
- `EIA_API_KEY`
- `MARKET_DATA_API_KEY`
- `AISHUB_USERNAME`

The Compose stack already sets:

- backend port `8005`
- frontend port `4173`
- SQLite path inside the data volume
- startup bootstrap and scheduled refresh enabled

## GitHub Setup

If this folder is not already a Git repository, initialize it locally:

```powershell
git init -b main
git add .
git commit -m "Initial macro stress dashboard"
```

Create an empty GitHub repository, then connect and push:

```powershell
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/macro_indicator_dashboard.git
git push -u origin main
```

GitHub Actions CI is already configured in:

- [D:\Data\OneDrive\Desktop\macro_indicator_dashboard\.github\workflows\ci.yml](D:/Data/OneDrive/Desktop/macro_indicator_dashboard/.github/workflows/ci.yml)

That workflow runs backend compile/tests and a frontend production build on push and pull request.

## DigitalOcean App Platform Setup

The repo includes an App Platform spec at:

- [D:\Data\OneDrive\Desktop\macro_indicator_dashboard\.do\app.yaml](D:/Data/OneDrive/Desktop/macro_indicator_dashboard/.do/app.yaml)

Before creating the app:

1. replace `YOUR_GITHUB_USERNAME/macro_indicator_dashboard` in `.do/app.yaml`
2. push the repository to GitHub
3. in DigitalOcean App Platform, create a new app from the GitHub repo
4. point App Platform at `.do/app.yaml`
5. add optional secrets such as `FRED_API_KEY`, `EIA_API_KEY`, `MARKET_DATA_API_KEY`, and `AISHUB_USERNAME` in the App Platform environment settings if you want those live feeds enabled

Recommended runtime shape:

- `frontend` is a static site
- `backend` is a single service instance so APScheduler only runs once
- `macro-db` is Postgres
- the backend is routed under `/api`

Notes:

- The backend keeps scheduled refresh enabled in the cloud.
- Postgres is the recommended cloud database because SQLite is not appropriate for this public App Platform deployment.
- The frontend is built to use `/api/v1` in production so it stays on a single public origin.

## Local Source Run

Use this only if you do not want Docker.

### 1. Backend install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python -m pip install --target vendor_py email-validator sniffio brotli
```

### 2. Frontend install

```powershell
cd frontend
npm install
cd ..
```

### 3. Configure environment

```powershell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

### 4. Seed and run

```powershell
.\scripts\seed_demo.ps1
.\scripts\start_backend.ps1
```

In a second terminal:

```powershell
.\scripts\start_frontend.ps1
```

## Running Tests

Backend:

```powershell
python -m pytest tests\backend -q
```

Frontend production build:

```powershell
cd frontend
npm run build
```

## Key Features

- Executive regime cards with Sticky / Convex / Break-Repression scores
- Causal chain view with recursive propagation
- Crisis monitor for fast-moving systemic stress signals
- Oil/shipping, funding, UST, domestic, and asset-regime panels
- Econometric state-space layer, analog matching, and forecast conditioning
- Manual and auto-scored overlays persisted to SQLite
- CSV import for custom series
- Event annotations
- Markdown export for daily summary
- Scheduled daily refresh via APScheduler

## Configuration

### Root `.env`

- `API_HOST`
- `API_PORT`
- `FRONTEND_ORIGIN`
- `DATABASE_URL`
- `DEMO_MODE`
- `SCHEDULER_ENABLED`
- `BOOTSTRAP_ON_STARTUP`
- `REFRESH_HOUR`
- `REFRESH_MINUTE`
- `ENABLE_ALERTS`
- `REGIME_CONFIG_PATH`

### Regime configuration

Edit:

- `backend/config/regime_config.json`

This controls:

- thresholds
- regime weights
- alert rules
- propagation edges
- state-space parameters

## Sharing and Upgrade Path

The Docker setup is optimized for:

- one-command local startup
- SQLite persistence in Docker volumes
- future prebuilt image support
- later migration to Postgres without changing the frontend or service layout

The current shared runtime is intentionally:

- two services only
- no browser auto-launch
- no host bind mounts required
- live-source by default with graceful degradation

## Known Limitations

- Some public feeds remain intermittent and may fall back or become unavailable on a given refresh
- The container starts on a deterministic bootstrap dataset and then performs live refresh asynchronously after startup
- `EUR/USD basis` and `JPY/USD basis` still require proxy support until a clean direct public source is integrated
- SQLite is appropriate for single-user local sharing, not multi-instance deployment
- The app is designed for one-user desktop/container use, not clustered production hosting

## Useful Files

- [backend/config/regime_config.json](D:/Data/OneDrive/Desktop/macro_indicator_dashboard/backend/config/regime_config.json)
- [docs/user_guide_revised.md](D:/Data/OneDrive/Desktop/macro_indicator_dashboard/docs/user_guide_revised.md)
- [docker-compose.yml](D:/Data/OneDrive/Desktop/macro_indicator_dashboard/docker-compose.yml)
