"""
KPI computation tasks using Polars DataFrames.
All computations done in-memory, only KPI results saved to database.
"""

import logging
from datetime import timedelta
from typing import List

import polars as pl
from celery import shared_task
from django.utils import timezone

from dashboard.models import (
    KPIOnTimePerformance,
    KPIAverageDelay,
    KPIHeadwayAdherence,
    KPIFeedFreshness,
    KPIServiceGaps,
    KPIOccupancy,
    Arrival,
    Occupancy,
)
from dashboard.gtfs_mbta_data import (
    load_mbta_vehicle_positions,
    load_mbta_trip_updates,
    load_mbta_static_gtfs,
    compute_scheduled_headways,
    get_time_window,
)

logger = logging.getLogger(__name__)

# KPI Parameters
DELAY_WINDOW_S = 60 * 60          # 60 minutes for OTP and delay
HEADWAY_WINDOW_S = 30 * 60        # 30 minutes for headways / gaps
PUNCTUALITY_THRESHOLD_S = 180      # 180s for "on time"
MAX_ABS_DELAY_S = 1800            # Clip outliers to ±30 min
SERVICE_GAP_FACTOR = 2.5          # k in gap definition
MIN_SAMPLE_SIZE = 5               # Minimum events to report


def load_arrivals_from_db(lookback_seconds: int = 7200) -> pl.DataFrame:
    """
    Load arrival records from database as Polars DataFrame.
    
    Args:
        lookback_seconds: How far back to look (default: 2 hours)
    
    Returns:
        Polars DataFrame with arrival data
    """
    cutoff = timezone.now() - timedelta(seconds=lookback_seconds)
    
    arrivals = Arrival.objects.filter(
        observed_at__gte=cutoff
    ).values(
        'route_id', 'stop_id', 'trip_id', 'vehicle_id',
        'observed_at', 'scheduled_at', 'delay_s'
    )
    
    if not arrivals:
        return pl.DataFrame()
    
    df = pl.DataFrame(list(arrivals))
    logger.info(f"Loaded {len(df)} arrival records from database")
    return df


def load_occupancy_from_db(lookback_seconds: int = 7200) -> pl.DataFrame:
    """
    Load occupancy records from database as Polars DataFrame.
    
    Args:
        lookback_seconds: How far back to look (default: 2 hours)
    
    Returns:
        Polars DataFrame with occupancy data
    """
    cutoff = timezone.now() - timedelta(seconds=lookback_seconds)
    
    occupancy = Occupancy.objects.filter(
        observed_at__gte=cutoff
    ).values(
        'route_id', 'vehicle_id', 'trip_id',
        'observed_at', 'ratio'
    )
    
    if not occupancy:
        return pl.DataFrame()
    
    df = pl.DataFrame(list(occupancy))
    logger.info(f"Loaded {len(df)} occupancy records from database")
    return df


@shared_task(name="kpi.compute_otp_and_average_delay")
def compute_otp_and_average_delay(window_seconds: int = DELAY_WINDOW_S):
    """
    Compute On-Time Performance (%) and Average Delay (s) by route.
    Reads arrival data from database and computes KPIs using Polars.
    """
    try:
        now, window_start, window_end = get_time_window(window_seconds)
        logger.info(f"Computing OTP and delay for window {window_start} to {window_end}")
        
        # Load arrivals from database (lookback 2x window to ensure coverage)
        departures = load_arrivals_from_db(lookback_seconds=window_seconds * 2)
        
        if len(departures) == 0:
            logger.warning("No departure events in database")
            return
        
        logger.info(f"Computed {len(departures)} departure events")
        
        # Filter to time window
        departures_window = departures.filter(
            (pl.col("observed_at") >= window_start) &
            (pl.col("observed_at") < window_end)
        )
        
        if len(departures_window) == 0:
            logger.info("No departures in current time window")
            return
        
        # Compute OTP by route
        # Filter outliers first (same as Average Delay) for consistency
        otp_df = (
            departures_window
            .filter(pl.col("delay_s").abs() <= MAX_ABS_DELAY_S)
            .with_columns([
                pl.when(pl.col("delay_s").abs() <= PUNCTUALITY_THRESHOLD_S)
                .then(1.0)
                .otherwise(0.0)
                .alias("on_time")
            ])
            .group_by("route_id")
            .agg([
                pl.col("on_time").mean().alias("otp_ratio"),
                pl.col("on_time").count().alias("sample_size")
            ])
            .filter(pl.col("sample_size") >= MIN_SAMPLE_SIZE)
            .with_columns([
                (pl.col("otp_ratio") * 100.0).alias("otp_percentage"),
                pl.lit(window_start).alias("window_start"),
                pl.lit(window_end).alias("window_end"),
                pl.lit(now).alias("created_at"),
                pl.lit(now).alias("updated_at")
            ])
        )
        
        # Compute Average Delay by route
        delay_df = (
            departures_window
            .filter(pl.col("delay_s").abs() <= MAX_ABS_DELAY_S)
            .group_by("route_id")
            .agg([
                pl.col("delay_s").mean().alias("average_delay_s"),
                pl.col("delay_s").count().alias("sample_size")
            ])
            .filter(pl.col("sample_size") >= MIN_SAMPLE_SIZE)
            .with_columns([
                pl.lit(window_start).alias("window_start"),
                pl.lit(window_end).alias("window_end"),
                pl.lit(now).alias("created_at"),
                pl.lit(now).alias("updated_at")
            ])
        )
        
        # Bulk upsert OTP
        if len(otp_df) > 0:
            otp_records = [
                KPIOnTimePerformance(
                    window_start=row["window_start"],
                    window_end=row["window_end"],
                    route_id=row["route_id"],
                    otp_percentage=row["otp_percentage"],
                    sample_size=row["sample_size"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in otp_df.to_dicts()
            ]
            KPIOnTimePerformance.objects.bulk_create(
                otp_records,
                update_conflicts=True,
                update_fields=["otp_percentage", "sample_size", "updated_at"],
                unique_fields=["window_start", "route_id"]
            )
            logger.info(f"Inserted {len(otp_records)} OTP KPIs")
        
        # Bulk upsert Average Delay
        if len(delay_df) > 0:
            delay_records = [
                KPIAverageDelay(
                    window_start=row["window_start"],
                    window_end=row["window_end"],
                    route_id=row["route_id"],
                    average_delay_s=row["average_delay_s"],
                    sample_size=row["sample_size"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in delay_df.to_dicts()
            ]
            KPIAverageDelay.objects.bulk_create(
                delay_records,
                update_conflicts=True,
                update_fields=["average_delay_s", "sample_size", "updated_at"],
                unique_fields=["window_start", "route_id"]
            )
            logger.info(f"Inserted {len(delay_records)} Average Delay KPIs")
        
    except Exception as e:
        logger.error(f"Failed to compute OTP and delay: {e}", exc_info=True)
        raise


@shared_task(name="kpi.compute_headway_adherence")
def compute_headway_adherence(window_seconds: int = HEADWAY_WINDOW_S):
    """
    Compute Headway Adherence (observed / scheduled) by route and stop.
    Reads arrival data from database and computes using Polars.
    """
    try:
        now, window_start, window_end = get_time_window(window_seconds)
        logger.info(f"Computing headway adherence for window {window_start} to {window_end}")
        
        # Load arrivals from database - USE ALL departures, not just window
        # Headway calculation needs consecutive events which may span beyond window
        # Lookback 3 hours to get enough consecutive events
        departures = load_arrivals_from_db(lookback_seconds=10800)
        
        if len(departures) == 0:
            logger.warning("No arrival data in database")
            return
        
        # Download static GTFS for scheduled headways
        static_gtfs = load_mbta_static_gtfs()
        
        if len(departures) == 0:
            logger.warning("No departure events")
            return
        
        logger.info(f"Computing headways from {len(departures)} total departure events")
        
        # Compute observed headways (time between consecutive departures at same stop/route)
        # Note: We use ALL departures to find consecutive pairs, then filter later
        observed_headways = (
            departures
            .sort(["route_id", "stop_id", "observed_at"])
            .with_columns([
                pl.col("observed_at")
                .diff()
                .over(["route_id", "stop_id"])
                .dt.total_seconds()
                .alias("headway_obs_s"),
                pl.col("observed_at").alias("current_time")
            ])
            .filter(
                pl.col("headway_obs_s").is_not_null() &
                (pl.col("headway_obs_s") > 0) &
                (pl.col("headway_obs_s") < 3600)  # Filter outliers > 1 hour
            )
        )
        
        if len(observed_headways) == 0:
            logger.info("No observed headways computed")
            return
        
        # Get scheduled headways from static GTFS
        scheduled_headways = compute_scheduled_headways(static_gtfs.get("stop_times"))
        
        if len(scheduled_headways) == 0:
            logger.warning("No scheduled headways available")
            return
        
        # Join observed with scheduled
        # Note: For headway adherence, we accept smaller sample sizes since data is sparse
        MIN_HEADWAY_SAMPLES = 1  # Lower threshold for headway data
        
        headway_adherence = (
            observed_headways
            .join(scheduled_headways, on="stop_id", how="inner")
            .filter(pl.col("headway_s") > 0)
            .with_columns([
                (pl.col("headway_obs_s") / pl.col("headway_s")).alias("adherence_ratio")
            ])
            .group_by(["route_id", "stop_id"])
            .agg([
                pl.col("adherence_ratio").mean().alias("adherence_ratio"),
                pl.col("adherence_ratio").count().alias("sample_size")
            ])
            .filter(pl.col("sample_size") >= MIN_HEADWAY_SAMPLES)
            .with_columns([
                pl.lit(window_start).alias("window_start"),
                pl.lit(window_end).alias("window_end"),
                pl.lit(now).alias("created_at"),
                pl.lit(now).alias("updated_at")
            ])
        )
        
        # Bulk upsert
        if len(headway_adherence) > 0:
            records = [
                KPIHeadwayAdherence(
                    window_start=row["window_start"],
                    window_end=row["window_end"],
                    route_id=row["route_id"],
                    stop_id=row["stop_id"],
                    adherence_ratio=row["adherence_ratio"],
                    sample_size=row["sample_size"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in headway_adherence.to_dicts()
            ]
            KPIHeadwayAdherence.objects.bulk_create(
                records,
                update_conflicts=True,
                update_fields=["adherence_ratio", "sample_size", "updated_at"],
                unique_fields=["window_start", "route_id", "stop_id"]
            )
            logger.info(f"Inserted {len(records)} Headway Adherence KPIs")
        
    except Exception as e:
        logger.error(f"Failed to compute headway adherence: {e}", exc_info=True)
        raise


@shared_task(name="kpi.compute_feed_freshness")
def compute_feed_freshness():
    """
    Compute feed freshness (age in seconds) for MBTA feeds.
    Downloads headers and calculates time since last update.
    """
    try:
        now = timezone.now()
        logger.info("Computing feed freshness")
        
        # Download feed data and get header timestamps
        vehicle_positions = load_mbta_vehicle_positions()
        trip_updates = load_mbta_trip_updates()
        
        feeds = []
        
        # Vehicle positions freshness
        if len(vehicle_positions) > 0 and "timestamp" in vehicle_positions.columns:
            latest_vp = vehicle_positions.select(pl.col("timestamp").max()).item()
            if latest_vp:
                from datetime import datetime
                header_ts = datetime.fromtimestamp(latest_vp, tz=timezone.get_current_timezone())
                freshness_s = int((now - header_ts).total_seconds())
                feeds.append({
                    "source": "mbta-vehicle-positions",
                    "freshness_s": freshness_s,
                    "observed_at": now,
                    "created_at": now
                })
        
        # Trip updates freshness
        if len(trip_updates) > 0 and "timestamp" in trip_updates.columns:
            latest_tu = trip_updates.select(pl.col("timestamp").max()).item()
            if latest_tu:
                from datetime import datetime
                header_ts = datetime.fromtimestamp(latest_tu, tz=timezone.get_current_timezone())
                freshness_s = int((now - header_ts).total_seconds())
                feeds.append({
                    "source": "mbta-trip-updates",
                    "freshness_s": freshness_s,
                    "observed_at": now,
                    "created_at": now
                })
        
        # Insert feed freshness KPIs
        if feeds:
            records = [
                KPIFeedFreshness(
                    observed_at=feed["observed_at"],
                    source=feed["source"],
                    freshness_s=feed["freshness_s"],
                    created_at=feed["created_at"]
                )
                for feed in feeds
            ]
            KPIFeedFreshness.objects.bulk_create(records)
            logger.info(f"Inserted {len(records)} Feed Freshness KPIs")
        
    except Exception as e:
        logger.error(f"Failed to compute feed freshness: {e}", exc_info=True)
        raise


@shared_task(name="kpi.compute_service_gaps")
def compute_service_gaps(window_seconds: int = HEADWAY_WINDOW_S):
    """
    Count service gaps (gaps > k * scheduled_headway) by route and stop.
    Reads arrival data from database and computes using Polars.
    """
    try:
        now, window_start, window_end = get_time_window(window_seconds)
        logger.info(f"Computing service gaps for window {window_start} to {window_end}")
        
        # Load arrivals from database - use broader window for gap detection
        # Lookback 3 hours to detect gaps properly
        departures = load_arrivals_from_db(lookback_seconds=10800)
        
        if len(departures) == 0:
            logger.warning("No arrival data in database")
            return
        
        # Download static GTFS for scheduled headways
        static_gtfs = load_mbta_static_gtfs()
        
        if len(departures) == 0:
            logger.warning("No departure events")
            return
        
        # Filter to time window
        departures_window = departures.filter(
            (pl.col("observed_at") >= window_start) &
            (pl.col("observed_at") < window_end)
        )
        
        if len(departures_window) == 0:
            logger.info("No departures in window")
            return
        
        # Compute gaps (time between consecutive departures)
        gaps = (
            departures_window
            .sort(["route_id", "stop_id", "observed_at"])
            .with_columns([
                pl.col("observed_at")
                .diff()
                .over(["route_id", "stop_id"])
                .dt.total_seconds()
                .alias("gap_s")
            ])
            .filter(
                pl.col("gap_s").is_not_null() &
                (pl.col("gap_s") > 0)
            )
        )
        
        if len(gaps) == 0:
            logger.info("No gaps computed")
            return
        
        # Get scheduled headways
        scheduled_headways = compute_scheduled_headways(static_gtfs.get("stop_times"))
        
        if len(scheduled_headways) == 0:
            logger.warning("No scheduled headways available")
            return
        
        # Join and count service gaps
        service_gaps = (
            gaps
            .join(scheduled_headways, on="stop_id", how="inner")
            .filter(pl.col("headway_s") > 0)
            .with_columns([
                (pl.col("gap_s") > SERVICE_GAP_FACTOR * pl.col("headway_s")).alias("is_gap")
            ])
            .group_by(["route_id", "stop_id"])
            .agg([
                pl.col("is_gap").sum().alias("gaps_count")
            ])
            .with_columns([
                pl.lit(window_start).alias("window_start"),
                pl.lit(window_end).alias("window_end"),
                pl.lit(now).alias("created_at"),
                pl.lit(now).alias("updated_at")
            ])
        )
        
        # Bulk upsert
        if len(service_gaps) > 0:
            records = [
                KPIServiceGaps(
                    window_start=row["window_start"],
                    window_end=row["window_end"],
                    route_id=row["route_id"],
                    stop_id=row["stop_id"],
                    gaps_count=int(row["gaps_count"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in service_gaps.to_dicts()
            ]
            KPIServiceGaps.objects.bulk_create(
                records,
                update_conflicts=True,
                update_fields=["gaps_count", "updated_at"],
                unique_fields=["window_start", "route_id", "stop_id"]
            )
            logger.info(f"Inserted {len(records)} Service Gaps KPIs")
        
    except Exception as e:
        logger.error(f"Failed to compute service gaps: {e}", exc_info=True)
        raise


@shared_task(name="kpi.compute_occupancy")
def compute_occupancy(window_seconds: int = DELAY_WINDOW_S):
    """
    Compute average occupancy by route.
    Reads occupancy data from database and computes using Polars.
    """
    try:
        now, window_start, window_end = get_time_window(window_seconds)
        logger.info(f"Computing occupancy for window {window_start} to {window_end}")
        
        # Load occupancy from database (lookback 2x window)
        occupancy = load_occupancy_from_db(lookback_seconds=window_seconds * 2)
        
        if len(occupancy) == 0:
            logger.warning("No occupancy data in database")
            return
        
        logger.info(f"Extracted {len(occupancy)} occupancy records")
        
        # Filter to time window
        occupancy_window = occupancy.filter(
            (pl.col("observed_at") >= window_start) &
            (pl.col("observed_at") < window_end)
        )
        
        if len(occupancy_window) == 0:
            logger.info("No occupancy in window")
            return
        
        # Compute average by route
        occupancy_kpi = (
            occupancy_window
            .group_by("route_id")
            .agg([
                pl.col("ratio").mean().alias("average_ratio"),
                pl.col("ratio").count().alias("sample_size")
            ])
            .filter(pl.col("sample_size") >= MIN_SAMPLE_SIZE)
            .with_columns([
                pl.lit(window_start).alias("window_start"),
                pl.lit(window_end).alias("window_end"),
                pl.lit(now).alias("created_at"),
                pl.lit(now).alias("updated_at")
            ])
        )
        
        # Bulk upsert
        if len(occupancy_kpi) > 0:
            records = [
                KPIOccupancy(
                    window_start=row["window_start"],
                    window_end=row["window_end"],
                    route_id=row["route_id"],
                    average_ratio=row["average_ratio"],
                    sample_size=row["sample_size"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in occupancy_kpi.to_dicts()
            ]
            KPIOccupancy.objects.bulk_create(
                records,
                update_conflicts=True,
                update_fields=["average_ratio", "sample_size", "updated_at"],
                unique_fields=["window_start", "route_id"]
            )
            logger.info(f"Inserted {len(records)} Occupancy KPIs")
        
    except Exception as e:
        logger.error(f"Failed to compute occupancy: {e}", exc_info=True)
        raise
