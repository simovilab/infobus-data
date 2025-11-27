"""
Admin interface for GTFS proxy models.
These provide read-only access to the main infobus database.
"""
from django.contrib import admin
from .models import Route, StopTime, Stop, Trip, Feed, Agency, GTFSProvider


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('route_short_name', 'route_long_name', 'route_type', 'feed')
    list_filter = ('route_type', 'feed')
    search_fields = ('route_short_name', 'route_long_name', 'route_id')
    readonly_fields = ('id', 'feed', 'route_id', 'agency_id', '_agency', 
                      'route_short_name', 'route_long_name', 'route_desc',
                      'route_type', 'route_url', 'route_color', 'route_text_color',
                      'route_sort_order')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StopTime)
class StopTimeAdmin(admin.ModelAdmin):
    list_display = ('trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time')
    list_filter = ('feed', 'pickup_type', 'drop_off_type')
    search_fields = ('trip_id', 'stop_id')
    readonly_fields = ('id', 'feed', 'trip_id', '_trip', 'arrival_time', 'departure_time',
                      'stop_id', '_stop', 'stop_sequence', 'stop_headsign',
                      'pickup_type', 'drop_off_type', 'shape_dist_traveled', 'timepoint')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ('stop_name', 'stop_id', 'stop_code', 'feed')
    list_filter = ('feed', 'location_type', 'wheelchair_boarding')
    search_fields = ('stop_name', 'stop_id', 'stop_code')
    readonly_fields = ('id', 'feed', 'stop_id', 'stop_code', 'stop_name',
                      'stop_heading', 'stop_desc', 'stop_lat', 'stop_lon',
                      'stop_point', 'zone_id', 'stop_url', 'location_type',
                      'parent_station', 'stop_timezone', 'wheelchair_boarding',
                      'platform_code', 'shelter', 'bench', 'lit', 'bay',
                      'device_charging_station')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('trip_id', 'route_id', 'trip_headsign', 'direction_id')
    list_filter = ('feed', 'direction_id', 'wheelchair_accessible', 'bikes_allowed')
    search_fields = ('trip_id', 'route_id', 'trip_headsign')
    readonly_fields = ('id', 'feed', 'route_id', '_route', 'service_id',
                      'trip_id', 'trip_headsign', 'trip_short_name',
                      'direction_id', 'block_id', 'shape_id',
                      'wheelchair_accessible', 'bikes_allowed')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ('feed_id', 'gtfs_provider', 'is_current', 'retrieved_at')
    list_filter = ('is_current', 'gtfs_provider')
    search_fields = ('feed_id',)
    readonly_fields = ('feed_id', 'gtfs_provider', 'http_etag', 'http_last_modified',
                      'is_current', 'retrieved_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
