# dashboard/tasks.py

from datetime import timedelta

from celery import shared_task
from django.db import connection
from django.utils import timezone

# --- Parámetros globales, alineados con el diccionario KPI ---

DELAY_WINDOW_S = 15 * 60          # 15 minutos para OTP y delay
HEADWAY_WINDOW_S = 30 * 60        # 30 minutos para headways / gaps
PUNCTUALITY_THRESHOLD_S = 60      # 60 s para considerar "on time"
MAX_ABS_DELAY_S = 1800            # recorte de outliers |delay| <= 30 min
SERVICE_GAP_FACTOR = 2.5          # k en la definición de service gaps
MIN_SAMPLE_SIZE = 5               # mínimo de eventos para reportar

# Django ya debe estar configurado con TIME_ZONE="America/Costa_Rica"


def _current_window(window_seconds: int):
    """
    Devuelve (now, window_start, window_end) alineado al minuto actual.
    """
    now = timezone.now()
    # Redondear hacia abajo al minuto
    window_end = now.replace(second=0, microsecond=0)
    window_start = window_end - timedelta(seconds=window_seconds)
    return now, window_start, window_end


# --------------------------------------------------------------------
# KPI 1 y 2 – On-Time Performance (%) y Average Delay (s)
# --------------------------------------------------------------------

@shared_task(name="kpi.compute_otp_and_average_delay")
def compute_otp_and_average_delay(window_seconds: int = DELAY_WINDOW_S):
    """
    Calcula:
      - OTP (%) por route_id
      - Average Delay (s) por route_id
    usando arrivals en la ventana [window_start, window_end).
    """
    now, window_start, window_end = _current_window(window_seconds)

    # First query: OTP
    sql_otp = """
    WITH base AS (
        SELECT
            route_id,
            COUNT(*)                                         AS sample_size,
            AVG(
                CASE
                    WHEN ABS(delay_s) <= %(punctuality_threshold)s
                        THEN 1.0
                    ELSE 0.0
                END
            )                                                AS otp_ratio
        FROM arrivals
        WHERE observed_at >= %(window_start)s
          AND observed_at <  %(window_end)s
        GROUP BY route_id
    )
    INSERT INTO kpi_on_time_performance AS otp
        (window_start, window_end, route_id,
         otp_percentage, sample_size, created_at, updated_at)
    SELECT
        %(window_start)s,
        %(window_end)s,
        route_id,
        otp_ratio * 100.0               AS otp_percentage,
        sample_size,
        %(now)s                         AS created_at,
        %(now)s                         AS updated_at
    FROM base
    WHERE sample_size >= %(min_sample_size)s
    ON CONFLICT (window_start, route_id) DO UPDATE
    SET otp_percentage = EXCLUDED.otp_percentage,
        sample_size    = EXCLUDED.sample_size,
        updated_at     = EXCLUDED.updated_at;
    """

    # Second query: Average Delay
    sql_delay = """
    WITH base AS (
        SELECT
            route_id,
            COUNT(*)                                         AS sample_size,
            AVG(delay_s) FILTER (
                WHERE ABS(delay_s) <= %(max_abs_delay)s
            )                                                AS avg_delay_s
        FROM arrivals
        WHERE observed_at >= %(window_start)s
          AND observed_at <  %(window_end)s
        GROUP BY route_id
    )
    INSERT INTO kpi_average_delay AS ad
        (window_start, window_end, route_id,
         average_delay_s, sample_size, created_at, updated_at)
    SELECT
        %(window_start)s,
        %(window_end)s,
        route_id,
        avg_delay_s,
        sample_size,
        %(now)s,
        %(now)s
    FROM base
    WHERE sample_size >= %(min_sample_size)s
    ON CONFLICT (window_start, route_id) DO UPDATE
    SET average_delay_s = EXCLUDED.average_delay_s,
        sample_size     = EXCLUDED.sample_size,
        updated_at      = EXCLUDED.updated_at;
    """

    params = {
        "now": now,
        "window_start": window_start,
        "window_end": window_end,
        "max_abs_delay": MAX_ABS_DELAY_S,
        "punctuality_threshold": PUNCTUALITY_THRESHOLD_S,
        "min_sample_size": MIN_SAMPLE_SIZE,
    }

    with connection.cursor() as cursor:
        cursor.execute(sql_otp, params)
        cursor.execute(sql_delay, params)


# --------------------------------------------------------------------
# KPI 3 – Headway Adherence (ratio)
# --------------------------------------------------------------------

@shared_task(name="kpi.compute_headway_adherence")
def compute_headway_adherence(window_seconds: int = HEADWAY_WINDOW_S):
    """
    Calcula Headway Adherence por route_id y stop_id:

      Headway_Adherence = observed_headway / scheduled_headway
    """
    now, window_start, window_end = _current_window(window_seconds)

    sql = """
    WITH arrivals_window AS (
        SELECT
            route_id,
            stop_id,
            observed_at,
            LAG(observed_at) OVER (
                PARTITION BY route_id, stop_id
                ORDER BY observed_at
            ) AS prev_observed_at
        FROM arrivals
        WHERE observed_at >= %(window_start)s
          AND observed_at <  %(window_end)s
    ),
    headways AS (
        SELECT
            route_id,
            stop_id,
            prev_observed_at,
            observed_at,
            EXTRACT(EPOCH FROM (observed_at - prev_observed_at)) AS headway_obs_s
        FROM arrivals_window
        WHERE prev_observed_at IS NOT NULL
    ),
    headways_with_sched AS (
        SELECT
            h.route_id,
            h.stop_id,
            h.headway_obs_s,
            sh.headway_s
        FROM headways h
        JOIN scheduled_headways sh
          ON sh.route_id = h.route_id
         AND sh.stop_id  = h.stop_id
         AND h.prev_observed_at >= sh.valid_from
         AND h.prev_observed_at <  sh.valid_to
        WHERE h.headway_obs_s > 0
          AND sh.headway_s > 0
    )
    INSERT INTO kpi_headway_adherence AS kha
        (window_start, window_end, route_id, stop_id,
         adherence_ratio, sample_size, created_at, updated_at)
    SELECT
        %(window_start)s,
        %(window_end)s,
        route_id,
        stop_id,
        AVG(headway_obs_s / headway_s) AS adherence_ratio,
        COUNT(*)                        AS sample_size,
        %(now)s                         AS created_at,
        %(now)s                         AS updated_at
    FROM headways_with_sched
    GROUP BY route_id, stop_id
    HAVING COUNT(*) >= %(min_sample_size)s
    ON CONFLICT (window_start, route_id, stop_id) DO UPDATE
    SET adherence_ratio = EXCLUDED.adherence_ratio,
        sample_size     = EXCLUDED.sample_size,
        updated_at      = EXCLUDED.updated_at;
    """

    params = {
        "now": now,
        "window_start": window_start,
        "window_end": window_end,
        "min_sample_size": MIN_SAMPLE_SIZE,
    }

    with connection.cursor() as cursor:
        cursor.execute(sql, params)


# --------------------------------------------------------------------
# KPI 4 – Feed Freshness (s)
# --------------------------------------------------------------------

@shared_task(name="kpi.compute_feed_freshness")
def compute_feed_freshness():
    """
    Calcula freshness_s = now - header.timestamp para cada source,
    y lo inserta como serie de tiempo en kpi_feed_freshness.
    """
    now = timezone.now()

    sql = """
    INSERT INTO kpi_feed_freshness (observed_at, source, freshness_s, created_at)
    SELECT
        %(now)s                      AS observed_at,
        source,
        EXTRACT(EPOCH FROM (%(now)s - last_header_ts))::bigint AS freshness_s,
        %(now)s                      AS created_at
    FROM feed_status;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, {"now": now})


# --------------------------------------------------------------------
# KPI 5 – Service Gaps (count)
# --------------------------------------------------------------------

@shared_task(name="kpi.compute_service_gaps")
def compute_service_gaps(window_seconds: int = HEADWAY_WINDOW_S):
    """
    Cuenta, por route_id y stop_id, cuántos gaps cumplen:

      gap_s > SERVICE_GAP_FACTOR * scheduled_headway
    en la ventana [window_start, window_end).
    """
    now, window_start, window_end = _current_window(window_seconds)

    sql = """
    WITH arrivals_window AS (
        SELECT
            route_id,
            stop_id,
            observed_at,
            LAG(observed_at) OVER (
                PARTITION BY route_id, stop_id
                ORDER BY observed_at
            ) AS prev_observed_at
        FROM arrivals
        WHERE observed_at >= %(window_start)s
          AND observed_at <  %(window_end)s
    ),
    gaps AS (
        SELECT
            route_id,
            stop_id,
            prev_observed_at,
            observed_at,
            EXTRACT(EPOCH FROM (observed_at - prev_observed_at)) AS gap_s
        FROM arrivals_window
        WHERE prev_observed_at IS NOT NULL
    ),
    gaps_with_sched AS (
        SELECT
            g.route_id,
            g.stop_id,
            g.gap_s,
            sh.headway_s
        FROM gaps g
        JOIN scheduled_headways sh
          ON sh.route_id = g.route_id
         AND sh.stop_id  = g.stop_id
         AND g.prev_observed_at >= sh.valid_from
         AND g.prev_observed_at <  sh.valid_to
        WHERE g.gap_s > 0
          AND sh.headway_s > 0
    )
    INSERT INTO kpi_service_gaps AS ksg
        (window_start, window_end, route_id, stop_id,
         gaps_count, created_at, updated_at)
    SELECT
        %(window_start)s,
        %(window_end)s,
        route_id,
        stop_id,
        COUNT(*) FILTER (
            WHERE gap_s > %(gap_factor)s * headway_s
        ) AS gaps_count,
        %(now)s AS created_at,
        %(now)s AS updated_at
    FROM gaps_with_sched
    GROUP BY route_id, stop_id
    ON CONFLICT (window_start, route_id, stop_id) DO UPDATE
    SET gaps_count = EXCLUDED.gaps_count,
        updated_at = EXCLUDED.updated_at;
    """

    params = {
        "now": now,
        "window_start": window_start,
        "window_end": window_end,
        "gap_factor": SERVICE_GAP_FACTOR,
    }

    with connection.cursor() as cursor:
        cursor.execute(sql, params)


# --------------------------------------------------------------------
# KPI 6 – Occupancy (ratio)
# --------------------------------------------------------------------

@shared_task(name="kpi.compute_occupancy")
def compute_occupancy(window_seconds: int = DELAY_WINDOW_S):
    """
    Calcula promedio de occupancy (0..1) por route_id en la ventana.
    """
    now, window_start, window_end = _current_window(window_seconds)

    sql = """
    INSERT INTO kpi_occupancy AS ko
        (window_start, window_end, route_id,
         average_ratio, sample_size, created_at, updated_at)
    SELECT
        %(window_start)s,
        %(window_end)s,
        route_id,
        AVG(ratio)       AS average_ratio,
        COUNT(*)         AS sample_size,
        %(now)s          AS created_at,
        %(now)s          AS updated_at
    FROM occupancy
    WHERE observed_at >= %(window_start)s
      AND observed_at <  %(window_end)s
    GROUP BY route_id
    HAVING COUNT(*) >= %(min_sample_size)s
    ON CONFLICT (window_start, route_id) DO UPDATE
    SET average_ratio = EXCLUDED.average_ratio,
        sample_size   = EXCLUDED.sample_size,
        updated_at    = EXCLUDED.updated_at;
    """

    params = {
        "now": now,
        "window_start": window_start,
        "window_end": window_end,
        "min_sample_size": MIN_SAMPLE_SIZE,
    }

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
