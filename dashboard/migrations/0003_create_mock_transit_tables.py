# Generated manually to create mock transit data tables for testing

from django.db import migrations
from django.utils import timezone
from datetime import timedelta


def create_tables_and_data(apps, schema_editor):
    """Create mock transit data tables and populate with test data"""
    
    # Get current time for generating recent data
    now = timezone.now()
    
    # SQL to create tables
    create_tables_sql = """
    -- Table: arrivals
    -- Stores bus arrival events with delay information
    CREATE TABLE IF NOT EXISTS arrivals (
        id BIGSERIAL PRIMARY KEY,
        route_id VARCHAR(64) NOT NULL,
        stop_id VARCHAR(64) NOT NULL,
        trip_id VARCHAR(128),
        vehicle_id VARCHAR(64),
        observed_at TIMESTAMPTZ NOT NULL,
        scheduled_at TIMESTAMPTZ,
        delay_s INTEGER NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_arrivals_observed_at ON arrivals(observed_at);
    CREATE INDEX IF NOT EXISTS idx_arrivals_route_stop ON arrivals(route_id, stop_id);
    
    -- Table: scheduled_headways
    -- Stores planned headways by route and stop
    CREATE TABLE IF NOT EXISTS scheduled_headways (
        id BIGSERIAL PRIMARY KEY,
        route_id VARCHAR(64) NOT NULL,
        stop_id VARCHAR(64) NOT NULL,
        headway_s INTEGER NOT NULL,
        valid_from TIMESTAMPTZ NOT NULL,
        valid_to TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_sched_headways_route_stop ON scheduled_headways(route_id, stop_id);
    CREATE INDEX IF NOT EXISTS idx_sched_headways_valid ON scheduled_headways(valid_from, valid_to);
    
    -- Table: feed_status
    -- Stores GTFS-RT feed metadata and timestamps
    CREATE TABLE IF NOT EXISTS feed_status (
        id BIGSERIAL PRIMARY KEY,
        source VARCHAR(128) NOT NULL UNIQUE,
        last_header_ts TIMESTAMPTZ NOT NULL,
        last_updated TIMESTAMPTZ DEFAULT NOW(),
        status VARCHAR(32) DEFAULT 'active'
    );
    
    -- Table: occupancy
    -- Stores vehicle occupancy observations
    CREATE TABLE IF NOT EXISTS occupancy (
        id BIGSERIAL PRIMARY KEY,
        route_id VARCHAR(64) NOT NULL,
        vehicle_id VARCHAR(64),
        trip_id VARCHAR(128),
        observed_at TIMESTAMPTZ NOT NULL,
        ratio FLOAT NOT NULL CHECK (ratio >= 0 AND ratio <= 1),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_occupancy_observed_at ON occupancy(observed_at);
    CREATE INDEX IF NOT EXISTS idx_occupancy_route ON occupancy(route_id);
    """
    
    schema_editor.execute(create_tables_sql)
    
    # Insert mock data
    # We'll generate data for the last 2 hours to ensure tasks find recent data
    
    # Insert scheduled headways (valid for a long time period)
    insert_headways_sql = """
    INSERT INTO scheduled_headways (route_id, stop_id, headway_s, valid_from, valid_to)
    VALUES
        ('101', 'STOP_A', 600, %(very_past)s, %(far_future)s),  -- 10 min headway
        ('101', 'STOP_B', 600, %(very_past)s, %(far_future)s),
        ('102', 'STOP_A', 900, %(very_past)s, %(far_future)s),  -- 15 min headway
        ('102', 'STOP_C', 900, %(very_past)s, %(far_future)s),
        ('103', 'STOP_B', 720, %(very_past)s, %(far_future)s),  -- 12 min headway
        ('103', 'STOP_C', 720, %(very_past)s, %(far_future)s)
    ON CONFLICT DO NOTHING;
    """
    
    # Insert feed status
    insert_feed_sql = """
    INSERT INTO feed_status (source, last_header_ts, last_updated)
    VALUES
        ('gtfs-rt-vehicle-positions', %(recent_ts)s, %(now)s),
        ('gtfs-rt-trip-updates', %(recent_ts)s, %(now)s)
    ON CONFLICT (source) DO UPDATE 
    SET last_header_ts = EXCLUDED.last_header_ts,
        last_updated = EXCLUDED.last_updated;
    """
    
    very_past = now - timedelta(days=365)
    far_future = now + timedelta(days=365)
    recent_ts = now - timedelta(minutes=2)  # Feed is 2 minutes old
    
    schema_editor.execute(insert_headways_sql, {
        'very_past': very_past,
        'far_future': far_future
    })
    
    schema_editor.execute(insert_feed_sql, {
        'recent_ts': recent_ts,
        'now': now
    })
    
    # Generate arrivals for the last 2 hours
    # This will create realistic patterns with some delays
    arrivals_data = []
    routes = [
        ('101', ['STOP_A', 'STOP_B']),
        ('102', ['STOP_A', 'STOP_C']),
        ('103', ['STOP_B', 'STOP_C'])
    ]
    
    # Generate arrivals every few minutes with varying delays
    for minutes_ago in range(120, 0, -3):  # Last 2 hours, every 3 minutes
        timestamp = now - timedelta(minutes=minutes_ago)
        
        for route_id, stops in routes:
            for stop_id in stops:
                # Generate realistic delays: most on time, some early, some late
                import random
                delay = random.choice([
                    -30, -20, -10, 0, 0, 0, 10, 20, 30,  # Most on time
                    45, 60, 90, 120, 150,  # Some late
                    -45, -60  # Some early
                ])
                
                trip_id = f"TRIP_{route_id}_{minutes_ago % 10}"
                vehicle_id = f"VEH_{route_id}_{(minutes_ago // 30) % 3}"
                
                arrivals_data.append((
                    route_id, stop_id, trip_id, vehicle_id,
                    timestamp, timestamp - timedelta(seconds=delay), delay
                ))
    
    # Batch insert arrivals
    if arrivals_data:
        arrivals_sql = """
        INSERT INTO arrivals (route_id, stop_id, trip_id, vehicle_id, 
                             observed_at, scheduled_at, delay_s)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        schema_editor.execute("DELETE FROM arrivals WHERE 1=1")  # Clear old data
        for arrival in arrivals_data:
            schema_editor.execute(arrivals_sql, arrival)
    
    # Generate occupancy data
    occupancy_data = []
    for minutes_ago in range(120, 0, -5):  # Every 5 minutes
        timestamp = now - timedelta(minutes=minutes_ago)
        
        for route_id, _ in routes:
            # Random occupancy between 0.1 and 0.9
            import random
            ratio = random.uniform(0.15, 0.85)
            vehicle_id = f"VEH_{route_id}_{(minutes_ago // 30) % 3}"
            trip_id = f"TRIP_{route_id}_{minutes_ago % 10}"
            
            occupancy_data.append((route_id, vehicle_id, trip_id, timestamp, ratio))
    
    # Batch insert occupancy
    if occupancy_data:
        occupancy_sql = """
        INSERT INTO occupancy (route_id, vehicle_id, trip_id, observed_at, ratio)
        VALUES (%s, %s, %s, %s, %s)
        """
        schema_editor.execute("DELETE FROM occupancy WHERE 1=1")  # Clear old data
        for occ in occupancy_data:
            schema_editor.execute(occupancy_sql, occ)
    
    print(f"✅ Created mock transit tables and inserted {len(arrivals_data)} arrivals and {len(occupancy_data)} occupancy records")


def drop_tables(apps, schema_editor):
    """Drop the mock tables if migration is reversed"""
    drop_sql = """
    DROP TABLE IF EXISTS arrivals CASCADE;
    DROP TABLE IF EXISTS scheduled_headways CASCADE;
    DROP TABLE IF EXISTS feed_status CASCADE;
    DROP TABLE IF EXISTS occupancy CASCADE;
    """
    schema_editor.execute(drop_sql)


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_timescale_hypertables'),
    ]

    operations = [
        migrations.RunPython(create_tables_and_data, drop_tables),
    ]
