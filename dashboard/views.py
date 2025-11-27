from django.shortcuts import render
from django.http import JsonResponse
from gtfs_proxy.models import Route, StopTime
from django.core.paginator import Paginator
import logging

logger = logging.getLogger(__name__)


def index(request):
    """Dashboard index page with GTFS data summary"""
    try:
        # Test connection to main database
        routes_count = Route.objects.using('infobus_main').count()
        stop_times_count = StopTime.objects.using('infobus_main').count()
        
        # Get some sample data
        routes = Route.objects.using('infobus_main')[:10]
        
        context = {
            'routes_count': routes_count,
            'stop_times_count': stop_times_count,
            'sample_routes': routes,
            'connection_status': 'Connected'
        }
    except Exception as e:
        logger.error(f"Error connecting to main database: {e}")
        context = {
            'routes_count': 0,
            'stop_times_count': 0,
            'sample_routes': [],
            'connection_status': f'Error: {str(e)}'
        }
    
    return render(request, 'dashboard/index.html', context)


def routes_api(request):
    """API endpoint to get routes from main database"""
    try:
        routes = Route.objects.using('infobus_main').values(
            'route_id', 'route_short_name', 'route_long_name', 'route_type'
        )[:20]
        
        return JsonResponse({
            'success': True,
            'data': list(routes),
            'count': len(routes)
        })
    except Exception as e:
        logger.error(f"Error fetching routes: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def stop_times_api(request):
    """API endpoint to get stop times from main database"""
    try:
        stop_times = StopTime.objects.using('infobus_main').select_related('_trip', '_stop').values(
            'trip_id', 'stop_id', 'arrival_time', 'departure_time', 'stop_sequence'
        )[:20]
        
        return JsonResponse({
            'success': True,
            'data': list(stop_times),
            'count': len(stop_times)
        })
    except Exception as e:
        logger.error(f"Error fetching stop times: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
