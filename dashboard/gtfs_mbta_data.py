# dashboard/gtfs_mbta_data.py
from __future__ import annotations

import io
import json
import logging
import tempfile
import zipfile
from datetime import datetime, date, timezone as dt_timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import polars as pl
import requests
from django.conf import settings
from django.utils import timezone as django_tz

logger = logging.getLogger(__name__)


def _download_file(url: str, max_retries: int = 3) -> bytes:
    """Download file with retry logic and error handling."""
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading from {url} (attempt {attempt + 1}/{max_retries})")
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            return resp.content
        except requests.exceptions.RequestException as e:
            logger.warning(f"Download attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
    raise RuntimeError(f"Failed to download {url} after {max_retries} attempts")




def load_mbta_static_gtfs() -> Dict[str, pl.DataFrame]:
    """Download and extract MBTA_GTFS.zip, return static GTFS dataframes.
    
    Uses system temp directory automatically.
    """
    try:
        zip_bytes = _download_file(settings.MBTA_GTFS_URL)
        
        # Use temporary directory that auto-cleans
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            zip_path = tmpdir_path / "MBTA_GTFS.zip"
            zip_path.write_bytes(zip_bytes)
            
            logger.info(f"Extracting GTFS zip to {tmpdir}")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir_path)
            
            dfs = {}
            # Standard GTFS file names (MBTA uses .txt with comma separators)
            gtfs_files = ["stops", "routes", "trips", "stop_times", "calendar", "calendar_dates"]
            
            for name in gtfs_files:
                file_path = tmpdir_path / f"{name}.txt"
                if file_path.exists():
                    logger.info(f"Loading {name}.txt")
                    # Force ID columns to be string to avoid parsing errors
                    if name == "stop_times":
                        dfs[name] = pl.read_csv(
                            file_path,
                            schema_overrides={
                                "trip_id": pl.Utf8,
                                "stop_id": pl.Utf8
                            }
                        )
                    elif name == "stops":
                        dfs[name] = pl.read_csv(
                            file_path,
                            schema_overrides={
                                "stop_id": pl.Utf8,
                                "parent_station": pl.Utf8
                            }
                        )
                    elif name == "trips":
                        dfs[name] = pl.read_csv(
                            file_path,
                            schema_overrides={
                                "route_id": pl.Utf8,
                                "service_id": pl.Utf8,
                                "trip_id": pl.Utf8,
                                "shape_id": pl.Utf8
                            }
                        )
                    elif name == "routes":
                        dfs[name] = pl.read_csv(
                            file_path,
                            schema_overrides={
                                "route_id": pl.Utf8,
                                "agency_id": pl.Utf8
                            }
                        )
                    else:
                        dfs[name] = pl.read_csv(file_path)
                else:
                    logger.warning(f"File {name}.txt not found in GTFS zip")
            
            return dfs
    except Exception as e:
        logger.error(f"Failed to load MBTA static GTFS: {e}")
        raise


def load_mbta_vehicle_positions() -> pl.DataFrame:
    """Load MBTA VehiclePositions JSON and return as DataFrame."""
    try:
        raw = _download_file(settings.MBTA_VEHICLEPOSITIONS_URL)
        data = json.loads(raw)
        
        # MBTA structure: {"header": {...}, "entity": [{"id": ..., "vehicle": {...}}, ...]}
        entities = data.get("entity", [])
        
        if not entities:
            logger.warning("No entities found in VehiclePositions feed")
            return pl.DataFrame()
        
        # Flatten the nested structure
        vehicles = []
        for entity in entities:
            vehicle_data = entity.get("vehicle", {})
            trip = vehicle_data.get("trip", {})
            position = vehicle_data.get("position", {})
            vehicle_info = vehicle_data.get("vehicle", {})
            
            vehicles.append({
                "entity_id": entity.get("id"),
                "trip_id": trip.get("trip_id"),
                "route_id": trip.get("route_id"),
                "direction_id": trip.get("direction_id"),
                "start_date": trip.get("start_date"),
                "start_time": trip.get("start_time"),
                "vehicle_id": vehicle_info.get("id"),
                "vehicle_label": vehicle_info.get("label"),
                "current_stop_sequence": vehicle_data.get("current_stop_sequence"),
                "stop_id": vehicle_data.get("stop_id"),
                "current_status": vehicle_data.get("current_status"),
                "timestamp": vehicle_data.get("timestamp"),
                "latitude": position.get("latitude"),
                "longitude": position.get("longitude"),
                "bearing": position.get("bearing"),
                "speed": position.get("speed"),
                "occupancy_status": vehicle_data.get("occupancy_status"),
                "occupancy_percentage": vehicle_data.get("occupancy_percentage"),
            })
        
        df = pl.DataFrame(vehicles)
        logger.info(f"Loaded {len(df)} vehicle positions")
        return df
        
    except Exception as e:
        logger.error(f"Failed to load MBTA vehicle positions: {e}")
        raise


def load_mbta_trip_updates() -> pl.DataFrame:
    """Load MBTA TripUpdates JSON and return as DataFrame."""
    try:
        raw = _download_file(settings.MBTA_TRIPUPDATES_URL)
        data = json.loads(raw)
        
        entities = data.get("entity", [])
        
        if not entities:
            logger.warning("No entities found in TripUpdates feed")
            return pl.DataFrame()
        
        # Flatten trip updates
        updates = []
        for entity in entities:
            trip_update = entity.get("trip_update", {})
            trip = trip_update.get("trip", {})
            vehicle = trip_update.get("vehicle", {})
            
            for stop_time_update in trip_update.get("stop_time_update", []):
                arrival = stop_time_update.get("arrival", {})
                departure = stop_time_update.get("departure", {})
                
                updates.append({
                    "entity_id": entity.get("id"),
                    "trip_id": trip.get("trip_id"),
                    "route_id": trip.get("route_id"),
                    "direction_id": trip.get("direction_id"),
                    "start_date": trip.get("start_date"),
                    "vehicle_id": vehicle.get("id"),
                    "stop_id": stop_time_update.get("stop_id"),
                    "stop_sequence": stop_time_update.get("stop_sequence"),
                    "arrival_time": arrival.get("time"),
                    "departure_time": departure.get("time"),
                    "timestamp": trip_update.get("timestamp"),
                })
        
        df = pl.DataFrame(updates)
        logger.info(f"Loaded {len(df)} trip update stop times")
        return df
        
    except Exception as e:
        logger.error(f"Failed to load MBTA trip updates: {e}")
        raise


def compute_departures_from_realtime(
    vehicle_positions: pl.DataFrame,
    trip_updates: pl.DataFrame,
) -> pl.DataFrame:
    """
    Compute departure events by joining realtime data with scheduled departure times.
    
    Uses vehicles with status STOPPED_AT or IN_TRANSIT_TO to capture departure events.
    The vehicle's timestamp represents the observation time.
    
    Returns DataFrame with columns:
    - route_id, stop_id, trip_id, vehicle_id
    - observed_at (actual observation timestamp)
    - scheduled_at (scheduled departure timestamp)
    - delay_s (difference in seconds)
    """
    try:
        # Filter for vehicles at stops or in transit
        # STOPPED_AT: vehicle currently at stop (can compute delay)
        # IN_TRANSIT_TO: vehicle heading to next stop (recently departed)
        active_vehicles = vehicle_positions.filter(
            pl.col("current_status").is_in(["STOPPED_AT", "IN_TRANSIT_TO"])
        )
        
        if len(active_vehicles) == 0:
            logger.warning("No active vehicles found")
            return pl.DataFrame()
        
        # Join with trip updates to get scheduled departure times
        # Match using trip_id and stop_sequence (current_stop_sequence from vehicle -> stop_sequence from trip_update)
        departures = (
            active_vehicles
            .rename({"current_stop_sequence": "stop_sequence"})  # Rename for join
            .join(
                trip_updates,
                on=["trip_id", "stop_sequence"],
                how="inner"
            )
            .filter(pl.col("departure_time").is_not_null())
            .select([
                pl.col("route_id"),
                pl.col("stop_id"),
                pl.col("stop_sequence"),
                pl.col("trip_id"),
                pl.col("vehicle_id"),
                pl.from_epoch(pl.col("timestamp"), time_unit="s").dt.replace_time_zone("UTC").alias("observed_at"),
                pl.from_epoch(pl.col("departure_time"), time_unit="s").dt.replace_time_zone("UTC").alias("scheduled_at"),
                (pl.col("timestamp") - pl.col("departure_time")).alias("delay_s")
            ])
        )
        
        logger.info(f"Computed {len(departures)} departure events")
        return departures
        
    except Exception as e:
        logger.error(f"Failed to compute departures: {e}")
        raise


def compute_occupancy_from_realtime(vehicle_positions: pl.DataFrame) -> pl.DataFrame:
    """
    Extract occupancy data from vehicle positions.
    
    Returns DataFrame with columns:
    - route_id, vehicle_id, trip_id
    - observed_at
    - ratio (occupancy as 0.0-1.0)
    """
    try:
        occupancy = (
            vehicle_positions
            .filter(
                pl.col("occupancy_percentage").is_not_null() &
                pl.col("route_id").is_not_null() &
                pl.col("timestamp").is_not_null()
            )
            .select([
                pl.col("route_id"),
                pl.col("vehicle_id"),
                pl.col("trip_id"),
                pl.from_epoch(pl.col("timestamp"), time_unit="s").dt.replace_time_zone("UTC").alias("observed_at"),
                (pl.col("occupancy_percentage") / 100.0).alias("ratio"),
            ])
        )
        
        logger.info(f"Extracted {len(occupancy)} occupancy records")
        return occupancy
        
    except Exception as e:
        logger.error(f"Failed to compute occupancy: {e}")
        raise


def compute_scheduled_headways(stop_times: pl.DataFrame) -> pl.DataFrame:
    """
    Compute scheduled headways from GTFS stop_times.txt.
    
    Returns DataFrame with columns:
    - stop_id (string)
    - headway_s (average scheduled headway in seconds)
    
    Note: This is a simplified version. Production systems would consider:
    - Service calendar (weekday/weekend/holiday)
    - Time of day variations
    - Direction
    """
    try:
        if stop_times is None or len(stop_times) == 0:
            logger.warning("No stop_times data provided")
            return pl.DataFrame({"stop_id": [], "headway_s": []}, schema={"stop_id": pl.Utf8, "headway_s": pl.Float64})
        
        # Ensure stop_id is string type
        if "stop_id" not in stop_times.columns:
            logger.warning("stop_id column not found in stop_times")
            return pl.DataFrame({"stop_id": [], "headway_s": []}, schema={"stop_id": pl.Utf8, "headway_s": pl.Float64})
        
        stop_times = stop_times.with_columns([
            pl.col("stop_id").cast(pl.Utf8)
        ])
        
        # Convert arrival_time to seconds since midnight
        # GTFS format: "HH:MM:SS" (can be > 24 hours for overnight service)
        def time_to_seconds(time_str: str) -> int:
            """Convert HH:MM:SS to seconds since midnight."""
            if not time_str or not isinstance(time_str, str):
                return None
            try:
                parts = time_str.split(":")
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except (ValueError, IndexError):
                return None
        
        # Calculate headways by stop
        headways = (
            stop_times
            .with_columns([
                pl.col("arrival_time").map_elements(time_to_seconds, return_dtype=pl.Int32).alias("arrival_seconds")
            ])
            .drop_nulls(subset=["arrival_seconds"])
            .sort(["stop_id", "arrival_seconds"])
            .with_columns([
                pl.col("arrival_seconds").diff().over("stop_id").alias("headway_s")
            ])
            .filter(pl.col("headway_s").is_not_null() & (pl.col("headway_s") > 0))
            .group_by(["stop_id"])
            .agg([
                pl.col("headway_s").mean().alias("headway_s")
            ])
        )
        
        logger.info(f"Computed headways for {len(headways)} stops")
        return headways
        
    except Exception as e:
        logger.error(f"Failed to compute scheduled headways: {e}", exc_info=True)
        # Return empty DataFrame with correct schema rather than raising
        return pl.DataFrame({"stop_id": [], "headway_s": []}, schema={"stop_id": pl.Utf8, "headway_s": pl.Float64})


def get_time_window(window_seconds: int):
    """
    Get current time window aligned to the minute.
    
    Args:
        window_seconds: Window size in seconds
    
    Returns:
        Tuple of (now, window_start, window_end) as timezone-aware datetimes
    """
    now = django_tz.now()
    # Align to minute boundary
    window_end = now.replace(second=0, microsecond=0)
    window_start = window_end - timedelta(seconds=window_seconds)
    return now, window_start, window_end
