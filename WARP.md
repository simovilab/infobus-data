# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Infobús Data** is a Django-based transit analytics platform that computes and tracks KPIs (Key Performance Indicators) for Costa Rica's public transit system. The project runs background tasks via Celery to analyze real-time GTFS data and provides a dashboard for visualization.

### Core Technology Stack

- **Django 5.2+** with Channels (ASGI) for async support
- **PostgreSQL 16** with TimescaleDB extension for time-series data
- **Redis** for Celery broker and Django Channels
- **Celery** with django-celery-beat for scheduled KPI computation
- **Daphne** as ASGI server
- **uv** for Python package management (via `pyproject.toml`)
- **Docker Compose** for containerized development

## Development Commands

### Starting the Application

```bash
# Development mode (recommended)
./scripts/dev.sh
# OR manually:
docker compose up --build -d

# Production mode (with Nginx)
./scripts/prod.sh
# OR manually:
docker compose -f docker-compose.production.yml --profile production up -d
```

### Docker Operations

```bash
# View logs
docker compose logs -f                    # All services
docker compose logs -f web                # Specific service
docker compose logs -f celery-worker      # Celery worker logs

# Restart services after code changes (hot reload handles most cases)
docker compose restart web
docker compose restart celery-worker celery-beat

# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v

# Execute commands in containers
docker compose exec web bash
docker compose exec web uv run python manage.py shell
```

### Django Management Commands

```bash
# Run migrations
docker compose exec web uv run python manage.py migrate

# Create migrations
docker compose exec web uv run python manage.py makemigrations

# Create superuser
docker compose exec web uv run python manage.py createsuperuser

# Collect static files
docker compose exec web uv run python manage.py collectstatic

# Django shell
docker compose exec web uv run python manage.py shell

# Run a single test
docker compose exec web uv run pytest path/to/test.py::test_name

# Run all tests
docker compose exec web uv run pytest
```

### Celery Operations

```bash
# View Celery worker status
docker compose exec celery-worker uv run celery -A infobus_data inspect active

# View scheduled tasks
docker compose exec celery-beat uv run celery -A infobus_data inspect scheduled

# Manually trigger a task (from Django shell)
docker compose exec web uv run python manage.py shell
>>> from dashboard.tasks import compute_otp_and_average_delay
>>> compute_otp_and_average_delay.delay()
```

### Database Operations

```bash
# Access PostgreSQL shell
docker compose exec db psql -U postgres -d infobus_data

# Run raw SQL query
docker compose exec web uv run python manage.py dbshell

# Check database connection
docker compose exec db pg_isready -U postgres
```

### Linting and Code Quality

```bash
# Run ruff linter
docker compose exec web uv run ruff check .

# Auto-fix with ruff
docker compose exec web uv run ruff check --fix .

# Format code
docker compose exec web uv run ruff format .
```

## Architecture

### Multi-Database Setup

This project uses **two PostgreSQL databases**:

1. **Local Database (`default`)** - Port 5433
   - Database name: `infobus_data`
   - Contains: KPI aggregation models, dashboard data, Celery results
   - Managed by: This application (migrations run here)

2. **Main Database (`infobus_main`)** - Port 5432
   - Database name: `infobus` (external)
   - Contains: GTFS data (routes, stops, trips, stop times, real-time data)
   - Accessed via: Proxy models in `gtfs_proxy` app
   - Mode: **Read-only access**

**Database Router** (`infobus_data/routers.py`):
- Routes all `gtfs_proxy` models to `infobus_main` database
- All other models use `default` database
- Prevents migrations on `gtfs_main` (managed externally)

### Django Apps Structure

1. **`infobus_data/`** - Main Django project configuration
   - `settings.py` - Multi-database config, Celery, Channels
   - `celery.py` - Celery app configuration
   - `routers.py` - Database routing logic
   - `urls.py` - Root URL configuration

2. **`dashboard/`** - KPI computation and storage
   - `models.py` - KPI aggregation models (OTP, Average Delay, Headway, Occupancy, etc.)
   - `tasks.py` - Celery tasks that compute KPIs from raw transit data
   - `views.py` - Dashboard API endpoints
   - **Key Models**: `KPIOnTimePerformance`, `KPIAverageDelay`, `KPIHeadwayAdherence`, `KPIFeedFreshness`, `KPIServiceGaps`, `KPIOccupancy`

3. **`gtfs_proxy/`** - Read-only access to main GTFS database
   - `models.py` - Proxy models that mirror main database schema
   - `admin.py` - Read-only admin interface for GTFS data
   - **Key Models**: `Route`, `Stop`, `Trip`, `StopTime`, `Feed`, `Agency`
   - **Usage**: Always query with `.using('infobus_main')`

4. **`website/`** - Public-facing website
   - Basic views and templates

### Celery Task Architecture

All KPI computation tasks are in `dashboard/tasks.py`. Each task:

1. Computes metrics for a **time window** (e.g., last 15 minutes)
2. Queries raw transit data from external tables (`arrivals`, `occupancy`, `scheduled_headways`, `feed_status`)
3. Aggregates data by route/stop
4. Uses `INSERT ... ON CONFLICT DO UPDATE` for idempotent writes

**Key Tasks**:
- `compute_otp_and_average_delay` - On-Time Performance (%) and Average Delay (seconds)
- `compute_headway_adherence` - Ratio of observed vs. scheduled headways
- `compute_feed_freshness` - GTFS-RT data staleness
- `compute_service_gaps` - Count of large gaps in service
- `compute_occupancy` - Average vehicle occupancy by route

**Task Parameters**:
- `DELAY_WINDOW_S = 900` (15 min) - For OTP/delay/occupancy
- `HEADWAY_WINDOW_S = 1800` (30 min) - For headways/gaps
- `PUNCTUALITY_THRESHOLD_S = 60` - ±60s is "on time"
- `SERVICE_GAP_FACTOR = 2.5` - Gaps > 2.5x scheduled headway

### Hot Reload in Development

The development environment includes **automatic hot reload** for all services:

- **Django (`web`)**: Auto-restarts when Python files change (built-in runserver)
- **Celery Worker**: Uses `watchmedo auto-restart` to reload on `.py` file changes
- **Celery Beat**: Schedules persist across restarts (stored in database)

Volume mounts exclude `.venv/` to prevent host/container conflicts.

### Static Files Handling

- **Development**: Django serves static files directly (when `DEBUG=True` or `DJANGO_SERVE_STATIC=True`)
- **Production**: Nginx serves static files from `/var/www/static` with aggressive caching
- Collected to `staticfiles/` via `manage.py collectstatic`

## Environment Configuration

The project uses a **layered environment file approach**:

1. `.env` - Base shared configuration (tracked in git)
2. `.env.dev` - Development overrides (tracked in git)
   - Sets `DEBUG=True`, `LOG_LEVEL=DEBUG`, etc.
3. `.env.local` - **Personal secrets and local overrides** (git-ignored)
   - Must contain `SECRET_KEY` for Django
   - Copy from `.env.local.example` to get started

**Windows-specific**: On Windows PowerShell, use the scripts with `bash` or WSL if available. Otherwise, run Docker Compose commands directly.

## Querying GTFS Data

When working with transit data from the main database:

```python
from gtfs_proxy.models import Route, StopTime, Stop

# Always specify .using('infobus_main')
routes = Route.objects.using('infobus_main').all()

# Filter and select related
stop_times = StopTime.objects.using('infobus_main').filter(
    trip_id='some_trip_id'
).select_related('_trip', '_stop').order_by('stop_sequence')

# Get route with agency info
route = Route.objects.using('infobus_main').select_related('_agency').first()
```

**Important**: These are read-only models. Do not attempt to `.save()` or `.delete()` on them.

## Key URLs

- **Development**: http://localhost:8000 (or check `WEB_PORT` in `.env.local`)
- **Admin**: http://localhost:8000/admin (default: admin/admin)
- **Dashboard**: http://localhost:8000/dashboard/
- **Health**: http://localhost:8000/health/
- **Grafana**: http://localhost:3000 (admin/admin)

**Production** (with Nginx):
- Website: http://localhost
- Static files served directly by Nginx

## Grafana Dashboards

Grafana is configured to visualize KPI data from PostgreSQL:

```bash
# Start Grafana
docker compose up -d grafana

# Access at http://localhost:3000
# Default credentials: admin/admin
```

**Available Dashboards**:
- **Transit KPIs Overview** - Main dashboard with all KPIs
  - On-Time Performance gauges by route
  - Average Delay time series
  - Headway Adherence trends
  - Feed Freshness monitoring
  - Service Gaps table

**Datasource**: Automatically configured to connect to `infobus_data` PostgreSQL database.

See `GRAFANA.md` for detailed dashboard documentation, SQL queries, and customization options.

## Testing KPI Computation

To manually trigger KPI computation:

```python
from dashboard.tasks import (
    compute_otp_and_average_delay,
    compute_headway_adherence,
    compute_feed_freshness,
    compute_service_gaps,
    compute_occupancy,
)

# Queue the task
task = compute_otp_and_average_delay.delay()

# Check task status
task.status  # 'PENDING', 'SUCCESS', 'FAILURE'
task.result  # Result or exception
```

View results in Django admin or query directly:

```python
from dashboard.models import KPIOnTimePerformance
KPIOnTimePerformance.objects.order_by('-window_start')[:10]
```

## Database Schema Notes

### Raw Transit Data Tables

These tables are **not Django models** but are queried directly in Celery tasks via raw SQL:

- `arrivals` - Bus arrival events with delay information
- `occupancy` - Vehicle occupancy observations
- `scheduled_headways` - Planned headways by route/stop (time-based)
- `feed_status` - GTFS-RT feed metadata and timestamps

### KPI Aggregation Tables

All KPI models in `dashboard/models.py` have:
- `window_start`, `window_end` - Time window for aggregation
- `route_id` (and sometimes `stop_id`) - Grouping dimensions
- `sample_size` - Number of observations used
- Unique constraints on `(window_start, route_id, ...)` for idempotent updates

## Troubleshooting

### Hot Reload Not Working

1. Check volume mounts: `docker compose config` should show `.:/app`
2. Ensure `PYTHONUNBUFFERED=1` is set
3. Restart the service: `docker compose restart web`

### Database Connection Issues

```bash
# Check if main infobus database is running
docker compose exec web uv run python manage.py dbshell --database=infobus_main

# Verify connection in Django shell
docker compose exec web uv run python manage.py shell
>>> from django.db import connections
>>> connections['infobus_main'].ensure_connection()
```

### Celery Tasks Not Running

```bash
# Check Celery worker logs
docker compose logs -f celery-worker

# Verify Redis connection
docker compose exec redis redis-cli ping

# Check scheduled tasks in Django admin
# Navigate to: Periodic Tasks (django-celery-beat)
```

### Static Files Not Loading

```bash
# Manually collect static files
docker compose exec web uv run python manage.py collectstatic --noinput

# Check DEBUG setting
docker compose exec web uv run python -c "from django.conf import settings; print(settings.DEBUG)"
```

## Project Locale

- **Language**: Spanish (Costa Rica) - `es-cr`
- **Timezone**: `America/Costa_Rica` (UTC-6)
- All timestamps in the database are timezone-aware
- Use `timezone.now()` from `django.utils.timezone` for current time

## When Making Changes

1. **Models**: After modifying models, always run `makemigrations` and `migrate`
2. **Tasks**: Celery worker auto-restarts in development, but beat schedules persist
3. **Static Files**: Run `collectstatic` if adding new CSS/JS (especially for production)
4. **Multi-DB Queries**: Remember to use `.using('infobus_main')` for GTFS proxy models
5. **Raw SQL**: All KPI tasks use raw SQL for performance; test queries in `psql` first
