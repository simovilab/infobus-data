import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "infobus_data.settings")

# Create a Celery application instance
app = Celery("infobus_data")

# Get settings from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps
app.autodiscover_tasks()

# Explicitly import MBTA ingestion tasks
import dashboard.mbta_ingestion_tasks  # noqa


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Celery request: {self.request!r}")
