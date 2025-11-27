# Generated manually to add MBTA data ingestion periodic task

from django.db import migrations
from django_celery_beat.models import PeriodicTask, IntervalSchedule


def create_ingestion_task(apps, schema_editor):
    """Create periodic task for MBTA data ingestion every 2 minutes."""
    
    # Create 2-minute interval schedule
    every_2_minutes, _ = IntervalSchedule.objects.get_or_create(
        every=2,
        period=IntervalSchedule.MINUTES,
    )
    
    # Create MBTA realtime ingestion task
    PeriodicTask.objects.get_or_create(
        name="MBTA: Ingest Realtime Data",
        defaults={
            "task": "mbta.ingest_realtime_data",
            "interval": every_2_minutes,
            "enabled": True,
            "description": "Fetch MBTA vehicle positions and trip updates every 2 minutes",
        }
    )
    
    # Create MBTA cleanup task (runs daily)
    every_day, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.DAYS,
    )
    
    PeriodicTask.objects.get_or_create(
        name="MBTA: Cleanup Old Data",
        defaults={
            "task": "mbta.cleanup_old_data",
            "interval": every_day,
            "enabled": True,
            "description": "Delete MBTA raw data older than 7 days",
        }
    )
    
    print("✅ Created MBTA ingestion periodic tasks")


def remove_ingestion_task(apps, schema_editor):
    """Remove MBTA ingestion periodic tasks."""
    PeriodicTask.objects.filter(
        name__in=[
            "MBTA: Ingest Realtime Data",
            "MBTA: Cleanup Old Data",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_cleanup_mock_and_raw_data'),
    ]

    operations = [
        migrations.RunPython(
            create_ingestion_task,
            remove_ingestion_task
        ),
    ]
