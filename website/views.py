from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis
from django.conf import settings

# Create your views here.


def index(request):
    return render(request, "index.html")


def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check Redis connection (if configured)
        try:
            redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "error"
        
        return JsonResponse({
            "status": "healthy",
            "database": "ok",
            "redis": redis_status,
        })
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status=503)


def hot_reload_test(request):
    """Test endpoint to demonstrate hot reload functionality."""
    return JsonResponse({
        "message": "🚀 Hot reload is AMAZING! File changes detected instantly! 🔥",
        "status": "success",
        "version": 2,
        "hot_reload": "active",
        "timestamp": "2025-09-17T02:57:00Z"
    })
