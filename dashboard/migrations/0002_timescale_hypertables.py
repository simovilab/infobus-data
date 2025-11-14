from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            """
            -- Asegúrate de que la extensión existe (si usas imagen de Timescale ya viene)
            CREATE EXTENSION IF NOT EXISTS timescaledb;

            -- Convertir tablas a hypertable
            SELECT create_hypertable(
                'kpi_on_time_performance',
                'window_start',
                if_not_exists => TRUE
            );

            SELECT create_hypertable(
                'kpi_average_delay',
                'window_start',
                if_not_exists => TRUE
            );

            SELECT create_hypertable(
                'kpi_headway_adherence',
                'window_start',
                if_not_exists => TRUE
            );

            SELECT create_hypertable(
                'kpi_feed_freshness',
                'observed_at',
                if_not_exists => TRUE
            );

            SELECT create_hypertable(
                'kpi_service_gaps',
                'window_start',
                if_not_exists => TRUE
            );

            SELECT create_hypertable(
                'kpi_occupancy',
                'window_start',
                if_not_exists => TRUE
            );

            -- Add unique constraints (now safe after hypertable conversion)
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_kpi_otp_window_route 
                ON kpi_on_time_performance (window_start, route_id);
            
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_kpi_avgdelay_window_route 
                ON kpi_average_delay (window_start, route_id);
            
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_kpi_headway_window_route_stop 
                ON kpi_headway_adherence (window_start, route_id, stop_id);
            
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_kpi_gaps_window_route_stop 
                ON kpi_service_gaps (window_start, route_id, stop_id);
            
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_kpi_occupancy_window_route 
                ON kpi_occupancy (window_start, route_id);

            -- Add additional indexes
            CREATE INDEX IF NOT EXISTS idx_otp_route_win 
                ON kpi_on_time_performance (route_id, window_start);
            
            CREATE INDEX IF NOT EXISTS idx_avgdelay_route_win 
                ON kpi_average_delay (route_id, window_start);
            
            CREATE INDEX IF NOT EXISTS idx_headway_route_stop_win 
                ON kpi_headway_adherence (route_id, stop_id, window_start);
            
            CREATE INDEX IF NOT EXISTS idx_feedfresh_source_obs 
                ON kpi_feed_freshness (source, observed_at);
            
            CREATE INDEX IF NOT EXISTS idx_gaps_route_stop_win 
                ON kpi_service_gaps (route_id, stop_id, window_start);
            
            CREATE INDEX IF NOT EXISTS idx_occupancy_route_win 
                ON kpi_occupancy (route_id, window_start);
            """,
            reverse_sql="""
            -- Reverse: solo por si quieres dropear todo
            DROP TABLE IF EXISTS kpi_occupancy;
            DROP TABLE IF EXISTS kpi_service_gaps;
            DROP TABLE IF EXISTS kpi_feed_freshness;
            DROP TABLE IF EXISTS kpi_headway_adherence;
            DROP TABLE IF EXISTS kpi_average_delay;
            DROP TABLE IF EXISTS kpi_on_time_performance;
            """,
        )
    ]
