"""
Proxy models to access GTFS data from the main infobus database.
These models mirror the structure of the main infobus GTFS models
but are configured to query the main database.
"""
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.db.models import UniqueConstraint


class Feed(models.Model):
    """Feed model - proxy to main database"""
    feed_id = models.CharField(max_length=100, primary_key=True, unique=True)
    gtfs_provider = models.ForeignKey(
        'GTFSProvider', on_delete=models.SET_NULL, blank=True, null=True
    )
    http_etag = models.CharField(max_length=1023, blank=True, null=True)
    http_last_modified = models.DateTimeField(blank=True, null=True)
    is_current = models.BooleanField(blank=True, null=True)
    retrieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False  # This model is managed by the main infobus app
        db_table = 'gtfs_feed'  # Use the actual table name from main DB
        app_label = 'gtfs_proxy'

    def __str__(self):
        return self.feed_id


class GTFSProvider(models.Model):
    """GTFS Provider model - proxy to main database"""
    provider_id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=31)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    schedule_url = models.URLField(blank=True, null=True)
    trip_updates_url = models.URLField(blank=True, null=True)
    vehicle_positions_url = models.URLField(blank=True, null=True)
    service_alerts_url = models.URLField(blank=True, null=True)
    timezone = models.CharField(max_length=63)
    is_active = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'gtfs_gtfsprovider'
        app_label = 'gtfs_proxy'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Agency(models.Model):
    """Agency model - proxy to main database"""
    id = models.BigAutoField(primary_key=True)
    feed = models.ForeignKey(Feed, to_field="feed_id", on_delete=models.CASCADE)
    agency_id = models.CharField(max_length=255, blank=True)
    agency_name = models.CharField(max_length=255)
    agency_url = models.URLField()
    agency_timezone = models.CharField(max_length=255)
    agency_lang = models.CharField(max_length=2, blank=True)
    agency_phone = models.CharField(max_length=127, blank=True, null=True)
    agency_fare_url = models.URLField(blank=True, null=True)
    agency_email = models.EmailField(max_length=254, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs_agency'
        app_label = 'gtfs_proxy'

    def __str__(self):
        return self.agency_name


class Route(models.Model):
    """Route model - proxy to main infobus database"""
    id = models.BigAutoField(primary_key=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    route_id = models.CharField(max_length=255)
    agency_id = models.CharField(max_length=200)
    _agency = models.ForeignKey(Agency, on_delete=models.CASCADE, blank=True, null=True)
    route_short_name = models.CharField(max_length=63, blank=True, null=True)
    route_long_name = models.CharField(max_length=255, blank=True, null=True)
    route_desc = models.TextField(blank=True, null=True)
    route_type = models.PositiveIntegerField(
        choices=(
            (0, "Tranvía o tren ligero"),
            (1, "Subterráneo o metro"),
            (2, "Ferrocarril"),
            (3, "Bus"),
            (4, "Ferry"),
            (5, "Teleférico"),
            (6, "Góndola"),
            (7, "Funicular"),
        ),
        default=3,
    )
    route_url = models.URLField(blank=True, null=True)
    route_color = models.CharField(max_length=6, blank=True, null=True)
    route_text_color = models.CharField(max_length=6, blank=True, null=True)
    route_sort_order = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False  # This model is managed by the main infobus app
        db_table = 'gtfs_route'  # Use the actual table name from main DB
        app_label = 'gtfs_proxy'

    def __str__(self):
        return f"{self.route_short_name}: {self.route_long_name}"


class Stop(models.Model):
    """Stop model - proxy to main database"""
    id = models.BigAutoField(primary_key=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    stop_id = models.CharField(max_length=255)
    stop_code = models.CharField(max_length=255, blank=True, null=True)
    stop_name = models.CharField(max_length=255)
    stop_heading = models.CharField(max_length=2, blank=True, null=True)
    stop_desc = models.TextField(blank=True, null=True)
    stop_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    stop_lon = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    stop_point = models.PointField(blank=True, null=True)
    zone_id = models.CharField(max_length=255, blank=True, null=True)
    stop_url = models.URLField(blank=True, null=True)
    location_type = models.PositiveIntegerField(blank=True, null=True)
    parent_station = models.CharField(max_length=255, blank=True)
    stop_timezone = models.CharField(max_length=255, blank=True)
    wheelchair_boarding = models.PositiveIntegerField(blank=True, null=True)
    platform_code = models.CharField(max_length=255, blank=True)
    shelter = models.BooleanField(blank=True, null=True)
    bench = models.BooleanField(blank=True, null=True)
    lit = models.BooleanField(blank=True, null=True)
    bay = models.BooleanField(blank=True, null=True)
    device_charging_station = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs_stop'
        app_label = 'gtfs_proxy'

    def __str__(self):
        return f"{self.stop_id}: {self.stop_name}"


class Trip(models.Model):
    """Trip model - proxy to main database"""
    id = models.BigAutoField(primary_key=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    route_id = models.CharField(max_length=200)
    _route = models.ForeignKey(Route, on_delete=models.CASCADE, blank=True, null=True)
    service_id = models.CharField(max_length=200)
    trip_id = models.CharField(max_length=255)
    trip_headsign = models.CharField(max_length=255, blank=True, null=True)
    trip_short_name = models.CharField(max_length=255, blank=True, null=True)
    direction_id = models.PositiveIntegerField(
        choices=((0, "En un sentido"), (1, "En el otro"))
    )
    block_id = models.CharField(max_length=255, blank=True, null=True)
    shape_id = models.CharField(max_length=255, blank=True, null=True)
    wheelchair_accessible = models.PositiveIntegerField(
        choices=((0, "No especificado"), (1, "Accesible"), (2, "No accesible"))
    )
    bikes_allowed = models.PositiveIntegerField(
        choices=((0, "No especificado"), (1, "Permitido"), (2, "No permitido"))
    )

    class Meta:
        managed = False
        db_table = 'gtfs_trip'
        app_label = 'gtfs_proxy'

    def __str__(self):
        return self.trip_id


class StopTime(models.Model):
    """StopTime model - proxy to main infobus database"""
    id = models.BigAutoField(primary_key=True)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    trip_id = models.CharField(max_length=200)
    _trip = models.ForeignKey(Trip, on_delete=models.CASCADE, blank=True, null=True)
    arrival_time = models.TimeField(blank=True, null=True)
    departure_time = models.TimeField(blank=True, null=True)
    stop_id = models.CharField(max_length=200)
    _stop = models.ForeignKey(Stop, on_delete=models.CASCADE, blank=True, null=True)
    stop_sequence = models.PositiveIntegerField()
    stop_headsign = models.CharField(max_length=255, blank=True, null=True)
    pickup_type = models.PositiveIntegerField()
    drop_off_type = models.PositiveIntegerField()
    shape_dist_traveled = models.DecimalField(
        max_digits=6, decimal_places=4, blank=True, null=True
    )
    timepoint = models.BooleanField(blank=True, null=True, default=False)

    class Meta:
        managed = False  # This model is managed by the main infobus app
        db_table = 'gtfs_stoptime'  # Use the actual table name from main DB
        app_label = 'gtfs_proxy'

    def __str__(self):
        return f"{self.trip_id}: {self.stop_id} ({self.stop_sequence})"
