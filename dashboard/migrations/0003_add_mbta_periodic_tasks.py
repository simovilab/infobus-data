# Generated manually to add MBTA data ingestion periodic tasks

from django.db import migrations
from django_celery_beat.models import PeriodicTask, IntervalSchedule


def create_mbta_periodic_tasks(apps, schema_editor):
    """Create periodic tasks for MBTA data ingestion."""
    
    # Create interval schedules
    every_minute, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.MINUTES,
    )
    
    every_day, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.DAYS,
    )
    
    # Create MBTA realtime ingestion task (runs every minute)
    PeriodicTask.objects.get_or_create(
        name="MBTA: Ingest Realtime Data",
        defaults={
            "task": "mbta.ingest_realtime_data",
            "interval": every_minute,
            "enabled": True,
            "description": "Fetch MBTA vehicle positions and trip updates every minute",
        }
    )
    
    # Create MBTA cleanup task (runs daily at 3 AM)
    PeriodicTask.objects.get_or_create(
        name="MBTA: Cleanup Old Data",
        defaults={
            "task": "mbta.cleanup_old_data",
            "interval": every_day,
            "enabled": True,
            "description": "Delete MBTA data older than 7 days",
        }
    )
    
    print("✅ Created MBTA periodic tasks")


def remove_mbta_periodic_tasks(apps, schema_editor):
    """Remove MBTA periodic tasks."""
    PeriodicTask.objects.filter(
        name__in=[
            "MBTA: Ingest Realtime Data",
            "MBTA: Cleanup Old Data",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_timescale_hypertables'),
    ]

    operations = [
        migrations.RunPython(
            create_mbta_periodic_tasks,
            remove_mbta_periodic_tasks
        ),
    ]
