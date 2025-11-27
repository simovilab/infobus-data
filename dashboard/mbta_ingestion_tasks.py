"""
MBTA Real-time Data Ingestion Tasks

This module contains Celery tasks for ingesting MBTA real-time data
into raw data tables. Tasks run periodically to fetch fresh data.
"""

import logging
from datetime import timedelta

import polars as pl
from celery import shared_task
from django.utils import timezone

from dashboard.gtfs_mbta_data import (
    load_mbta_vehicle_positions,
    load_mbta_trip_updates,
    compute_departures_from_realtime,
    compute_occupancy_from_realtime,
)

logger = logging.getLogger(__name__)


@shared_task(name="mbta.ingest_realtime_data")
def ingest_mbta_realtime_data():
    """
    Ingest MBTA real-time data into raw data tables.
    
    Downloads fresh MBTA vehicle positions and trip updates,
    processes them with Polars, and stores in database tables:
    - arrivals: Bus/train arrival events with delays
    - occupancy: Vehicle occupancy observations
    - feed_status: Feed health monitoring
    
    Runs every 2 minutes via Celery Beat.
    """
    from dashboard.models import Arrival, Occupancy, FeedStatus
    
    try:
        now = timezone.now()
        logger.info("Starting MBTA realtime data ingestion")
        
        # Download fresh MBTA data
        logger.info("Downloading MBTA vehicle positions")
        vehicle_positions = load_mbta_vehicle_positions()
        
        logger.info("Downloading MBTA trip updates")
        trip_updates = load_mbta_trip_updates()
        
        if len(vehicle_positions) == 0 or len(trip_updates) == 0:
            logger.warning("No vehicle positions or trip updates available")
            return {"arrivals": 0, "occupancy": 0, "timestamp": now.isoformat()}
        
        logger.info(f"Loaded {len(vehicle_positions)} vehicle positions")
        logger.info(f"Loaded {len(trip_updates)} trip update stop times")
        
        # Compute departures (arrivals)
        departures_df = compute_departures_from_realtime(vehicle_positions, trip_updates)
        
        if len(departures_df) == 0:
            logger.warning("No departure events computed")
            arrivals_count = 0
        else:
            # Convert to Arrival model instances
            arrival_records = [
                Arrival(
                    route_id=row["route_id"],
                    stop_id=row["stop_id"],
                    trip_id=row["trip_id"],
                    vehicle_id=row["vehicle_id"],
                    observed_at=row["observed_at"],
                    scheduled_at=row["scheduled_at"],
                    delay_s=row["delay_s"],
                    created_at=now,
                )
                for row in departures_df.to_dicts()
            ]
            
            # Bulk insert arrivals
            Arrival.objects.bulk_create(arrival_records, ignore_conflicts=True)
            arrivals_count = len(arrival_records)
            logger.info(f"Inserted {arrivals_count} arrival records")
        
        # Compute occupancy
        occupancy_df = compute_occupancy_from_realtime(vehicle_positions)
        
        if len(occupancy_df) == 0:
            logger.warning("No occupancy data computed")
            occupancy_count = 0
        else:
            # Convert to Occupancy model instances
            occupancy_records = [
                Occupancy(
                    route_id=row["route_id"],
                    vehicle_id=row["vehicle_id"],
                    trip_id=row.get("trip_id"),
                    ratio=row["ratio"],
                    observed_at=row["observed_at"],
                    created_at=now,
                )
                for row in occupancy_df.to_dicts()
            ]
            
            # Bulk insert occupancy
            Occupancy.objects.bulk_create(occupancy_records, ignore_conflicts=True)
            occupancy_count = len(occupancy_records)
            logger.info(f"Inserted {occupancy_count} occupancy records")
        
        # Update feed status
        from datetime import datetime, timezone as dt_timezone
        
        for source, df in [
            ("mbta-vehicle-positions", vehicle_positions),
            ("mbta-trip-updates", trip_updates),
        ]:
            if len(df) > 0 and "timestamp" in df.columns:
                last_timestamp = df["timestamp"].max()
                if last_timestamp:
                    last_header_ts = datetime.fromtimestamp(last_timestamp, tz=dt_timezone.utc)
                    
                    FeedStatus.objects.update_or_create(
                        source=source,
                        defaults={
                            "last_header_ts": last_header_ts,
                            "status": "active",
                        },
                    )
        
        logger.info(
            f"MBTA ingestion completed: {arrivals_count} arrivals, "
            f"{occupancy_count} occupancy records"
        )
        
        return {
            "arrivals": arrivals_count,
            "occupancy": occupancy_count,
            "timestamp": now.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest MBTA realtime data: {e}", exc_info=True)
        raise


@shared_task(name="mbta.cleanup_old_data")
def cleanup_old_mbta_data(days: int = 7):
    """
    Delete MBTA raw data older than specified days.
    
    Args:
        days: Number of days to retain (default: 7)
    
    Runs daily via Celery Beat.
    """
    from dashboard.models import Arrival, Occupancy
    
    try:
        cutoff = timezone.now() - timedelta(days=days)
        
        arrivals_deleted = Arrival.objects.filter(created_at__lt=cutoff).delete()[0]
        occupancy_deleted = Occupancy.objects.filter(created_at__lt=cutoff).delete()[0]
        
        logger.info(
            f"Cleanup completed: deleted {arrivals_deleted} arrivals, "
            f"{occupancy_deleted} occupancy records older than {days} days"
        )
        
        return {
            "arrivals_deleted": arrivals_deleted,
            "occupancy_deleted": occupancy_deleted,
            "cutoff": cutoff.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old MBTA data: {e}", exc_info=True)
        raise
