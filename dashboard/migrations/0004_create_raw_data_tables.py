# Generated migration to create raw data tables if they don't exist

from django.db import migrations


def create_raw_tables(apps, schema_editor):
    """
    Create raw data tables used transiently for KPI computation.
    These tables are not Django models but needed for data processing.
    """
    create_tables_sql = """
    -- Table: arrivals
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
    CREATE TABLE IF NOT EXISTS feed_status (
        id BIGSERIAL PRIMARY KEY,
        source VARCHAR(128) NOT NULL UNIQUE,
        last_header_ts TIMESTAMPTZ NOT NULL,
        last_updated TIMESTAMPTZ DEFAULT NOW(),
        status VARCHAR(32) DEFAULT 'active'
    );
    
    -- Table: occupancy
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


def drop_raw_tables(apps, schema_editor):
    """Drop raw data tables."""
    drop_sql = """
    DROP TABLE IF EXISTS arrivals CASCADE;
    DROP TABLE IF NOT EXISTS scheduled_headways CASCADE;
    DROP TABLE IF EXISTS feed_status CASCADE;
    DROP TABLE IF EXISTS occupancy CASCADE;
    """
    schema_editor.execute(drop_sql)


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_add_mbta_periodic_tasks'),
    ]

    operations = [
        migrations.RunPython(create_raw_tables, drop_raw_tables),
    ]
