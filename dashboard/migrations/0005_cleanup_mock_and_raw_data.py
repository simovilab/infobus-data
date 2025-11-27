# Generated migration to cleanup mock data and old ingestion infrastructure

from django.db import migrations


def cleanup_raw_tables(apps, schema_editor):
    """
    Truncate raw data tables and remove MBTA ingestion periodic tasks.
    Raw tables are kept for backward compatibility but should remain empty.
    """
    # Truncate raw data tables
    truncate_sql = """
    TRUNCATE TABLE arrivals CASCADE;
    TRUNCATE TABLE occupancy CASCADE;
    TRUNCATE TABLE scheduled_headways CASCADE;
    TRUNCATE TABLE feed_status CASCADE;
    """
    schema_editor.execute(truncate_sql)
    
    # Remove MBTA ingestion periodic tasks from django-celery-beat
    # These are no longer needed - KPI tasks download data directly
    remove_tasks_sql = """
    DELETE FROM django_celery_beat_periodictask 
    WHERE name IN ('MBTA: Ingest Realtime Data', 'MBTA: Cleanup Old Data');
    """
    schema_editor.execute(remove_tasks_sql)


def reverse_cleanup(apps, schema_editor):
    """No reverse operation - data cleanup is intentional"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_create_raw_data_tables'),
    ]

    operations = [
        migrations.RunPython(cleanup_raw_tables, reverse_cleanup),
    ]
