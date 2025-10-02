# KPI Dictionary (v1.1) — PostgreSQL/TimescaleDB + Django/Celery + Grafana

KPIs are computed/stored in **PostgreSQL/TimescaleDB** by **Django/Celery** jobs and visualized in **Grafana via SQL**.

## Scope & Data Pipeline
- **Sources**
  - **GTFS Schedule (PostgreSQL)**: `routes`, `trips`, `stop_times`, `calendar`, `calendar_dates`.
  - **GTFS‑Realtime / Infobús**: `vehicle_positions`, `trip_updates` (when available), `header.timestamp`.
- **Pipeline**
  - **Django + Celery** ingest/transform at fixed intervals (e.g., 5–30 s for RT, 5–15 min for aggregates).
  - Data lands in **TimescaleDB hypertables** (e.g., `arrivals`, `feed_status`).
  - KPIs are exposed via **SQL views** / **continuous aggregates** and consumed directly in Grafana panels.
- **Timezone**: America/Costa_Rica.
- **Rolling Windows (suggested)**
  - Delay/OTP: **15 min** (`delay_window_s`).
  - Headway/gaps: **30 min** (`headway_window_s`).

## Schema & Naming (suggested)
- `arrivals(route_id, stop_id, trip_id, scheduled_ts, actual_ts, delay_s, observed_at)` — one row per observed arrival (or per control-point event).
- `scheduled_headways(route_id, stop_id, timeband, headway_s, valid_from, valid_to)` — precomputed schedule headways by band.
- `feed_status(source, last_header_ts, last_seen_ts)` — latest GTFS‑RT status per source.
- `occupancy(route_id, vehicle_id, ratio, observed_at)` — when available.

---

## KPI 1 — On‑Time Performance (OTP, %)
**Definition**: Compare actual arrivals and departures against planned ones.
Share of events with absolute delay ≤ threshold (e.g., 60 s).  
**Formula**  
\[
OTP(\%) = \frac{|\{e\in E : |delay_e| \le \theta\}|}{|E|} \times 100
\]
with \( delay_e = t^{real}_e - t^{sched}_e \) and \(\theta\) = punctuality threshold (default 60 s).  
**Inputs**: scheduled time (`stop_times.arrival_time`) vs. real time (from `trip_updates` or stop pass inference).  
**Units**: percent (0–100).  
**Metric**: `pt_on_time_percentage{route_id}` *(Gauge)*.  
**Assumptions**: early events (negative delay) count if |delay| ≤ θ; configurable threshold.  
**Edge cases**: pickup/drop‑off only stops; few events in window — report `sample_size` or suppress when |E| < N_min.

---

## KPI 2 — Average Delay (s)
**Definition**: Average Delay would refer to the typical deviation from the planned schedule, calculated in seconds, where a positive value means bus is late and a negative value means it's early.   
**Formula**  
\[
\overline{delay} = \frac{1}{|E|}\sum_{e\in E}(t^{real}_e - t^{sched}_e)
\]
**Units**: seconds (may be negative).  
**Metric**: `pt_average_delay_seconds{route_id}` *(Gauge)*.  
**Assumptions**: trim outliers (e.g., percentiles 1–99 or |delay| ≤ 1800 s).  
**Edge cases**: short‑turns, partial trips, schedule changes.

---

## KPI 3 — Headway Adherence (ratio)
**Definition**: Refers to the comparison of actual vehicle headways (time between consecutive vehicles) against scheduled headways to measure service regularity. 
**Formula**  
\[
Headway_Adherence(ratio) = Observed headway / scheduled headway at control points.
\]
BUNCHING: When vehicles are much closer together than scheduled. 
GAPPING: When there is a larger-than-expected gap between vehicles.   
**How**:  
- **Scheduled**: derive headway from `stop_times` for time band (peak/off‑peak) at chosen `stop_id`.  
- **Observed**: deltas between consecutive real arrivals at that `stop_id`.  
**Units**: ratio (1.0 ideal; >1.0 gaps; <1.0 bunching risk).  
**Metric**: `pt_headway_adherence_ratio{route_id}` (optionally `stop_id`).  
**Assumptions**: need ≥3 arrivals in window for stability; exclude layovers.  
**Edge cases**: terminals with multiple in/out passes; irregular headways.

---

## KPI 4 — Feed Freshness (s)
**Definition**: Age of GTFS‑RT feed.  
**Formula**  
\[
freshness\_s = now() - header.timestamp
\]
**Units**: seconds.  
**Metric**: `pt_feed_age_seconds`.  
**Assumptions**: server clock synced (NTP).  
**Edge cases**: missing/future timestamps — emit NaN/omit and alert.

---

## KPI 5 — Service Gaps (count)
**Definition**: Missing or incomplete portion of a transit agency's scheduled or real-time services that are not accurately represented or published within their GTFS data. 
Count of periods with no bus observed **> k × scheduled headway**.  
**Concept**  
\[
gap = \mathbb{1}\{t_{no\_vehicles} > k \cdot headway_{sched}\}
\]
accumulated within window.  
**Units**: integer count.  
**Metric**: `pt_service_gaps_count{route_id}`.  
**Assumptions**: k - TBD (`service_gap_factor`) 
**Edge cases**: off‑service hours — use calendar to avoid false positives.

---

## KPI 6 — Occupancy (ratio, if available)
**Definition**: Vehicle load factor 0..1.  
**Computation**:  
- If feed exposes `occupancy_percentage` → use 0..1 (or convert 0..100%).  
- If only `occupancy_status` (discrete), map to ratio (e.g., `MANY_SEATS_AVAILABLE` ≈ 0.2, `FEW_SEATS_AVAILABLE` ≈ 0.8, `FULL` = 1.0).  
**Metric**: `pt_occupancy_ratio{route_id}` (or by vehicle if needed).  
**Assumptions**: do not emit when missing.  
**Edge cases**: heterogeneous agency conventions; sparse sampling.

---

## Data Quality & Validation
- Clock sync (NTP); stable identifiers (`route_id`, `stop_id`).
- Report `sample_size` for transparency when low.
- Validate OTP/Delay by time‑of‑day; headways at named control points.
- Keep **view** names stable for Grafana dashboards.
