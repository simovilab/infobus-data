# MBTA Data Integration

This document explains how the project integrates with MBTA (Massachusetts Bay Transportation Authority) real-time transit data.

## Overview

The system automatically fetches and processes MBTA GTFS-RT data every minute to compute transit KPIs.

## Data Sources

### 1. MBTA GTFS Static
- **URL**: https://cdn.mbta.com/MBTA_GTFS.zip
- **Format**: ZIP containing standard GTFS text files
- **Update frequency**: Daily (as needed)
- **Contents**: routes, stops, trips, stop_times, calendar, etc.

### 2. MBTA Vehicle Positions
- **URL**: https://cdn.mbta.com/realtime/VehiclePositions.json
- **Format**: GTFS-RT JSON (enhanced)
- **Update frequency**: Real-time (~30 seconds)
- **Data**: Current vehicle locations, occupancy, status

### 3. MBTA Trip Updates
- **URL**: https://cdn.mbta.com/realtime/TripUpdates.json
- **Format**: GTFS-RT JSON
- **Update frequency**: Real-time (~30 seconds)
- **Data**: Predicted arrival/departure times per stop

## Architecture

### Data Flow

```
MBTA APIs
    ↓
gtfs_mbta_data.py (Polars DataFrames)
    ↓
mbta_ingestion_tasks.py (Celery Task)
    ↓
PostgreSQL Tables (arrivals, occupancy, feed_status)
    ↓
KPI Computation Tasks (tasks.py)
    ↓
KPI Tables & Grafana Dashboards
```

### Key Components

1. **`dashboard/gtfs_mbta_data.py`**
   - Functions to download and parse MBTA data
   - Uses Polars for efficient data processing
   - Flattens nested JSON into DataFrames

2. **`dashboard/mbta_ingestion_tasks.py`**
   - Celery tasks for periodic data ingestion
   - `ingest_mbta_realtime_data()` - Runs every minute
   - `cleanup_old_mbta_data()` - Runs daily

3. **Database Tables**
   - `arrivals` - Bus arrival events with delays
   - `occupancy` - Vehicle occupancy observations
   - `feed_status` - Feed health monitoring

## Configuration

### Environment Variables

Add to your `.env.local`:

```bash
# MBTA Data Sources (defaults shown)
MBTA_GTFS_URL=https://cdn.mbta.com/MBTA_GTFS.zip
MBTA_TRIPUPDATES_URL=https://cdn.mbta.com/realtime/TripUpdates.json
MBTA_VEHICLEPOSITIONS_URL=https://cdn.mbta.com/realtime/VehiclePositions.json
```

### Periodic Tasks

Configured in `dashboard/migrations/0004_add_mbta_periodic_tasks.py`:

- **MBTA: Ingest Realtime Data** - Every 1 minute
- **MBTA: Cleanup Old Data** - Every 1 day

View/edit in Django Admin: http://localhost:8000/admin/django_celery_beat/periodictask/

## Running the Integration

### 1. Apply Migrations

```bash
docker compose exec web uv run python manage.py migrate dashboard
```

This will:
- Create the periodic task schedules
- Add tasks to Celery Beat

### 2. Verify Celery Workers

```bash
# Check that workers are running
docker compose ps celery-worker celery-beat

# View worker logs
docker compose logs -f celery-worker

# View beat logs
docker compose logs -f celery-beat
```

### 3. Manual Test (Optional)

Test the ingestion manually:

```bash
docker compose exec web uv run python manage.py shell
```

```python
from dashboard.mbta_ingestion_tasks import ingest_mbta_realtime_data

# Run the task manually
result = ingest_mbta_realtime_data()
print(result)
# Should return: {'arrivals': N, 'occupancy': M, 'timestamp': '...'}
```

### 4. Monitor Ingestion

Check that data is being ingested:

```bash
# View recent arrivals
docker compose exec db psql -U postgres -d infobus_data -c "
  SELECT COUNT(*), MAX(observed_at) as latest 
  FROM arrivals 
  WHERE observed_at >= NOW() - INTERVAL '10 minutes';
"

# View occupancy data
docker compose exec db psql -U postgres -d infobus_data -c "
  SELECT COUNT(*), MAX(observed_at) as latest 
  FROM occupancy 
  WHERE observed_at >= NOW() - INTERVAL '10 minutes';
"

# Check feed status
docker compose exec db psql -U postgres -d infobus_data -c "
  SELECT * FROM feed_status WHERE source LIKE 'mbta-%';
"
```

## Data Processing Details

### Arrival Events

Computed by joining:
1. **Vehicle Positions** - Actual vehicle location/time
2. **Trip Updates** - Scheduled arrival times
3. **Calculation**: `delay_s = actual_time - scheduled_time`

Only includes vehicles with status:
- `STOPPED_AT` - Vehicle at stop
- `IN_TRANSIT_TO` - Vehicle approaching stop

### Occupancy Data

Extracted directly from Vehicle Positions:
- `occupancy_percentage` → converted to ratio (0.0-1.0)
- Only includes vehicles reporting occupancy data

### Feed Freshness

Tracks last update timestamp for monitoring:
- `last_header_ts` - Latest data timestamp from MBTA
- `last_updated` - When we last fetched the data
- `status` - active/error

## Troubleshooting

### Task Not Running

1. Check Celery Beat is running:
   ```bash
   docker compose logs celery-beat --tail=50
   ```

2. Verify task is enabled in Django Admin:
   http://localhost:8000/admin/django_celery_beat/periodictask/

3. Manually trigger the task:
   ```bash
   docker compose exec web uv run python manage.py shell -c "
   from dashboard.mbta_ingestion_tasks import ingest_mbta_realtime_data;
   ingest_mbta_realtime_data.delay()
   "
   ```

### No Data Being Inserted

1. Check worker logs for errors:
   ```bash
   docker compose logs celery-worker -f | grep -i "mbta\|error"
   ```

2. Test MBTA API connectivity:
   ```bash
   curl -I https://cdn.mbta.com/realtime/VehiclePositions.json
   ```

3. Run task in foreground to see detailed errors:
   ```python
   from dashboard.mbta_ingestion_tasks import ingest_mbta_realtime_data
   ingest_mbta_realtime_data()  # Will show full traceback
   ```

### Data Quality Issues

Check feed freshness:
```sql
SELECT 
  source,
  last_header_ts,
  last_updated,
  EXTRACT(EPOCH FROM (NOW() - last_updated)) as seconds_since_update,
  status
FROM feed_status 
WHERE source LIKE 'mbta-%';
```

If `seconds_since_update` > 120 (2 minutes), the feed may be stale.

## Performance Considerations

### Data Retention

- Default: 7 days of historical data
- Adjust in migration or via task parameter:
  ```python
  cleanup_old_mbta_data(days_to_keep=14)  # Keep 2 weeks
  ```

### Ingestion Frequency

- Current: Every 1 minute
- MBTA updates: ~30 seconds
- To increase frequency, edit the periodic task schedule in Django Admin

### Database Size Estimates

Assuming ~500 vehicles, ~10,000 stops:
- Arrivals: ~500 records/minute = ~720,000/day = ~5M/week
- With 7-day retention: ~35M arrival records
- Estimated size: ~5-10 GB with indexes

## Next Steps

1. **Add scheduled_headways computation** - Calculate from static GTFS
2. **Implement route filtering** - Only ingest specific routes if needed
3. **Add alerting** - Notify when feeds are stale
4. **Optimize queries** - Add indexes for common query patterns
5. **Add data validation** - Check for anomalies in delays/occupancy

## References

- [MBTA V3 API Documentation](https://www.mbta.com/developers/v3-api)
- [GTFS Realtime Reference](https://gtfs.org/realtime/)
- [Polars Documentation](https://pola-rs.github.io/polars/)
