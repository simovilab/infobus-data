from django.db import models


class KPIOnTimePerformance(models.Model):
    """
    On-Time Performance (OTP) por ruta en ventanas de tiempo.
    otp_percentage está en el rango 0-100 (no 0-1).
    """
    window_start = models.DateTimeField(db_index=True)
    window_end = models.DateTimeField()
    route_id = models.CharField(max_length=64, db_index=True)

    otp_percentage = models.FloatField(
        help_text="On-time performance en porcentaje (0-100)."
    )
    sample_size = models.IntegerField(
        help_text="Número de eventos (arrivals) usados para el cálculo."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kpi_on_time_performance"
        verbose_name = "On-Time Performance"
        verbose_name_plural = "On-Time Performance KPIs"
        constraints = [
            models.UniqueConstraint(
                fields=["window_start", "route_id"],
                name="uniq_kpi_otp_window_route",
            ),
        ]
        indexes = [
            models.Index(fields=["route_id", "window_start"], name="idx_otp_route_win"),
        ]

    def __str__(self):
        return f"OTP {self.route_id} @ {self.window_start:%Y-%m-%d %H:%M}"


class KPIAverageDelay(models.Model):
    """
    Delay promedio (en segundos) por ruta en ventanas de tiempo.
    Incluye sample_size para poder filtrar ventanas poco representativas.
    """
    window_start = models.DateTimeField(db_index=True)
    window_end = models.DateTimeField()
    route_id = models.CharField(max_length=64, db_index=True)

    average_delay_s = models.FloatField(
        help_text="Delay promedio en segundos (positivo=atraso, negativo=adelanto)."
    )
    sample_size = models.IntegerField(
        help_text="Número de eventos (arrivals) usados para el cálculo."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kpi_average_delay"
        verbose_name = "Average Delay"
        verbose_name_plural = "Average Delay KPIs"
        constraints = [
            models.UniqueConstraint(
                fields=["window_start", "route_id"],
                name="uniq_kpi_avgdelay_window_route",
            ),
        ]
        indexes = [
            models.Index(
                fields=["route_id", "window_start"],
                name="idx_avgdelay_route_win",
            ),
        ]

    def __str__(self):
        return f"AvgDelay {self.route_id} @ {self.window_start:%Y-%m-%d %H:%M}"


class KPIHeadwayAdherence(models.Model):
    """
    Adherencia de headway, típico ratio headway_observado / headway_programado
    por ruta y parada en ventanas de tiempo.
    """
    window_start = models.DateTimeField(db_index=True)
    window_end = models.DateTimeField()
    route_id = models.CharField(max_length=64, db_index=True)
    stop_id = models.CharField(max_length=64, db_index=True)

    adherence_ratio = models.FloatField(
        help_text="Promedio de headway_observado / headway_programado."
    )
    sample_size = models.IntegerField(
        help_text="Número de pares de arribos usados para el cálculo."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kpi_headway_adherence"
        verbose_name = "Headway Adherence"
        verbose_name_plural = "Headway Adherence KPIs"
        constraints = [
            models.UniqueConstraint(
                fields=["window_start", "route_id", "stop_id"],
                name="uniq_kpi_headway_window_route_stop",
            ),
        ]
        indexes = [
            models.Index(
                fields=["route_id", "stop_id", "window_start"],
                name="idx_headway_route_stop_win",
            ),
        ]

    def __str__(self):
        return (
            f"Headway {self.route_id}/{self.stop_id} "
            f"@ {self.window_start:%Y-%m-%d %H:%M}"
        )


class KPIFeedFreshness(models.Model):
    """
    Freshness del feed GTFS-RT / Infobús en segundos.
    Se almacena como serie de tiempo (cada vez que corre la tarea).
    """
    observed_at = models.DateTimeField(db_index=True)
    source = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Identificador de la fuente, p.ej. 'databus-gtfs-rt'.",
    )
    freshness_s = models.BigIntegerField(
        help_text="Diferencia en segundos entre now() y header.timestamp."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kpi_feed_freshness"
        verbose_name = "Feed Freshness"
        verbose_name_plural = "Feed Freshness KPIs"
        indexes = [
            models.Index(
                fields=["source", "observed_at"],
                name="idx_feedfresh_source_obs",
            ),
        ]

    def __str__(self):
        return f"Freshness {self.source} = {self.freshness_s}s @ {self.observed_at}"


class KPIServiceGaps(models.Model):
    """
    Service Gaps por ruta y parada en ventanas de tiempo.
    gaps_count normalmente cuenta cuántos gaps superan k * headway_programado.
    """
    window_start = models.DateTimeField(db_index=True)
    window_end = models.DateTimeField()
    route_id = models.CharField(max_length=64, db_index=True)
    stop_id = models.CharField(max_length=64, db_index=True)

    gaps_count = models.IntegerField(
        help_text="Cantidad de gaps que superan el umbral definido."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kpi_service_gaps"
        verbose_name = "Service Gaps"
        verbose_name_plural = "Service Gaps KPIs"
        constraints = [
            models.UniqueConstraint(
                fields=["window_start", "route_id", "stop_id"],
                name="uniq_kpi_gaps_window_route_stop",
            ),
        ]
        indexes = [
            models.Index(
                fields=["route_id", "stop_id", "window_start"],
                name="idx_gaps_route_stop_win",
            ),
        ]

    def __str__(self):
        return (
            f"Gaps {self.route_id}/{self.stop_id} "
            f"@ {self.window_start:%Y-%m-%d %H:%M}: {self.gaps_count}"
        )


class KPIOccupancy(models.Model):
    """
    Ocupación promedio por ruta en ventanas de tiempo.
    average_ratio suele ser 0..1 (fracción de ocupación).
    """
    window_start = models.DateTimeField(db_index=True)
    window_end = models.DateTimeField()
    route_id = models.CharField(max_length=64, db_index=True)

    average_ratio = models.FloatField(
        help_text="Ocupación promedio en el rango 0-1."
    )
    sample_size = models.IntegerField(
        help_text="Número de observaciones de occupancy usadas."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kpi_occupancy"
        verbose_name = "Occupancy"
        verbose_name_plural = "Occupancy KPIs"
        constraints = [
            models.UniqueConstraint(
                fields=["window_start", "route_id"],
                name="uniq_kpi_occupancy_window_route",
            ),
        ]
        indexes = [
            models.Index(
                fields=["route_id", "window_start"],
                name="idx_occupancy_route_win",
            ),
        ]

    def __str__(self):
        return (
            f"Occ {self.route_id} @ {self.window_start:%Y-%m-%d %H:%M} "
            f"= {self.average_ratio:.2f}"
        )

