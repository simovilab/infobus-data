# GTFS Integration with Main Infobus Database

This document explains how **infobus-data** can query GTFS data (routes and stop times) from the main **infobus** database.

## Architecture

- **Main Database** (infobus): localhost:5432 - Contains GTFS data (routes, stop times, etc.)
- **Local Database** (infobus_data): localhost:5433 - Contains dashboard-specific data
- **Cross-database queries** enabled through Django's multiple database support

## Configuration

### 1. Multiple Database Setup
Located in `infobus_data/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'infobus_data',
        'USER': 'postgres', 
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5433',
    },
    'infobus_main': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'infobus',
        'USER': 'postgres',
        'PASSWORD': 'postgres', 
        'HOST': 'localhost',
        'PORT': '5432',
    },
}
```

### 2. Database Router
Routes GTFS proxy model queries to the main database (`infobus_data/routers.py`).

### 3. Proxy Models
Located in `gtfs_proxy/models.py` - these models mirror the main GTFS models but are configured to query the main database.

## Usage Examples

### In Views (dashboard/views.py)

```python
from gtfs_proxy.models import Route, StopTime

# Get routes from main database
routes = Route.objects.using('infobus_main').all()

# Get stop times with filtering
stop_times = StopTime.objects.using('infobus_main').filter(
    trip_id='some_trip_id'
).select_related('_trip', '_stop')

# Count total records
routes_count = Route.objects.using('infobus_main').count()
stop_times_count = StopTime.objects.using('infobus_main').count()
```

### In Django Shell

```python
# Query routes
from gtfs_proxy.models import Route, StopTime

# Get all routes
routes = Route.objects.using('infobus_main').all()

# Get routes for specific feed
routes = Route.objects.using('infobus_main').filter(feed_id='some_feed')

# Get stop times for a route
stop_times = StopTime.objects.using('infobus_main').filter(
    _trip__route_id='route_123'
).order_by('stop_sequence')

# Get route details with related data
route = Route.objects.using('infobus_main').select_related('_agency').first()
print(f"Route: {route.route_short_name} - {route.route_long_name}")
```

### API Endpoints

Access GTFS data via REST API:

- **Routes API**: `GET /dashboard/api/routes/`
- **Stop Times API**: `GET /dashboard/api/stop-times/`

## Available Models

All located in `gtfs_proxy.models`:

- **Route**: Transit routes with route_short_name, route_long_name, etc.
- **StopTime**: Arrival/departure times at stops for specific trips  
- **Stop**: Bus stops with coordinates and details
- **Trip**: Individual trips on routes
- **Feed**: GTFS feed information
- **Agency**: Transit agencies

## Testing the Integration

### 1. Start Both Applications

```bash
# Terminal 1 - Main Infobus (port 8000)
cd infobus
docker compose up -d

# Terminal 2 - Infobus Data (port 8001) 
cd infobus-data
docker compose up -d
```

### 2. Access the Dashboard

Visit: http://localhost:8001/dashboard/

This shows:
- Connection status to main database
- Count of routes and stop times
- Sample routes from main database
- API endpoints for testing

### 3. Admin Interface

Visit: http://localhost:8001/admin/

Navigate to "GTFS Proxy Models" section to browse:
- Routes (read-only)
- Stop Times (read-only) 
- Stops, Trips, Feeds (read-only)

## Key Features

✅ **Cross-database queries** - Query main DB from infobus-data
✅ **Read-only access** - Cannot modify main database from dashboard
✅ **Django ORM integration** - Use familiar Django query syntax  
✅ **Admin interface** - Browse GTFS data via Django admin
✅ **API endpoints** - REST APIs for routes and stop times
✅ **Automatic routing** - Database router handles query routing

## Environment Variables

Add to `.env.local`:

```bash
# Main Infobus Database Connection (for GTFS data)
MAIN_DB_NAME=infobus
MAIN_DB_USER=postgres  
MAIN_DB_PASSWORD=postgres
MAIN_DB_HOST=localhost
MAIN_DB_PORT=5432
```

## Troubleshooting

1. **Connection errors**: Ensure main infobus is running on port 5432
2. **Table not found**: Check that main database has GTFS tables populated
3. **Permission errors**: Verify database user has SELECT permissions
4. **Port conflicts**: Ensure ports 5432 and 5433 are available

This integration allows the infobus-data dashboard to efficiently query and display transit data from the main infobus system while maintaining separate databases for different concerns.
