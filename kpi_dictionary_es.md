# Diccionario de KPIs (v1.1) — PostgreSQL/TimescaleDB + Django/Celery + Grafana

**PostgreSQL/TimescaleDB** mediante tareas de **Django/Celery** y se visualizan en **Grafana con SQL**.

## Alcance y flujo de datos
- **Fuentes**
  - **GTFS Schedule (PostgreSQL)**: `routes`, `trips`, `stop_times`, `calendar`, `calendar_dates`.
  - **GTFS‑RT / Infobús**: `vehicle_positions`, `trip_updates` (cuando exista), `header.timestamp`.
- **Pipeline**
  - **Django + Celery** ingiere/transforma en intervalos fijos (p. ej., 5–30 s para RT, 5–15 min para agregados).
  - Los datos se guardan en **hypertables de TimescaleDB** (p. ej., `arrivals`, `feed_status`).
  - Los KPIs se exponen mediante **vistas SQL** / **agregados continuos** y Grafana los consume por SQL.
- **Zona horaria**: America/Costa_Rica.
- **Ventanas sugeridas**
  - Demora/OTP: **15 min** (`delay_window_s`).
  - Headway/gaps: **30 min** (`headway_window_s`).

## Esquema y nombres (sugeridos)
- `arrivals(route_id, stop_id, trip_id, scheduled_ts, actual_ts, delay_s, observed_at)` — una fila por llegada observada (o evento en punto de control).
- `scheduled_headways(route_id, stop_id, timeband, headway_s, valid_from, valid_to)` — headways programados por franja.
- `feed_status(source, last_header_ts, last_seen_ts)` — estado reciente del feed GTFS‑RT por fuente.
- `occupancy(route_id, vehicle_id, ratio, observed_at)` — cuando exista.

---

## KPI 1 — On‑Time Performance (OTP, %)
**Definición**: Comparación de llegadas y salidas reales contra horario planeado. Porcentaje de eventos con |demora| ≤ umbral (p. ej. 60 s).  
**Fórmula**  
\[
OTP(\%) = \frac{|\{e\in E : |delay_e| \le \theta\}|}{|E|} \times 100
\]
Donde \( delay_e = t^{real}_e - t^{prog}_e \) y \(\theta\) = umbral de puntualidad (pendiente de definir).  
**Entradas**: hora programada (`stop_times.arrival_time`) vs hora real (de `trip_updates` o inferida por paso).  
**Unidades**: porcentaje (0–100).  
**Métrica**: `pt_on_time_percentage{route_id}` *(Gauge)*.  
**Supuestos**: eventos tempranos (delay < 0) cuentan si |delay| ≤ θ; umbral configurable.  
**Casos borde**: paradas solo pick‑up/drop‑off; pocas observaciones — reportar `sample_size` o suprimir si |E| < N_min.

---

## KPI 2 — Demora promedio (s)
**Definición**: La demora promedio se refiere a la desviación del horario planificado, calculada en segundos; un valor positivo indica que el bus está retrasado y uno negativo que está adelantado.
**Fórmula**  
\[
\overline{delay} = \frac{1}{|E|}\sum_{e\in E}(t^{real}_e - t^{prog}_e)
\]
**Unidades**: segundos (puede ser negativo).  
**Métrica**: `pt_average_delay_seconds{route_id}` *(Gauge)*.  
**Supuestos**: recortar valores atípicos (p. ej., percentiles 1–99 o |delay| ≤ 1800 s). Usar ventana de tiempo para el calculo, medir promedio por ruta. 


---

## KPI 3 — Cumplimiento de headway (ratio)
**Definición**: Se refiere a la comparación de los intervalos de tiempo reales entre vehículos (tiempo entre vehículos consecutivos) frente a los intervalos programados para medir la regularidad del servicio.

headway(ratio) = headway observado / headway programado en puntos de control.  

BUNCHING (agrupamiento): cuando los vehículos (buses) circulan mucho más cerca entre sí de lo programado.
GAPPING (brecha/hueco de servicio): cuando hay un intervalo de tiempo entre vehículos mayor al esperado.
**Cómo**:  
- **Programado**: usar `stop_times` para la ventana de tiempo en el `stop_id` elegido.  
- **Observado**: diferencias entre llegadas reales consecutivas en ese `stop_id`.  
**Unidades**: adimensional (1.0 ideal; >1.0 huecos; <1.0 riesgo de bunching).  
**Métrica**: `pt_headway_adherence_ratio{route_id}`  (opcional `stop_id`).  
**Supuestos**: ≥3 llegadas en la ventana; excluir layovers.  
**Casos borde**: terminales con múltiples entradas/salidas; headways irregulares.

---

## KPI 4 — Frescura del feed (s)
**Definición**: antigüedad del GTFS‑RT.  
**Fórmula**  
\[
freshness\_s = now() - header.timestamp
\]
**Unidades**: segundos.  
**Métrica**: `pt_feed_age_seconds`.  
**Supuestos**: reloj del servidor sincronizado (NTP).  
**Casos borde**: timestamps ausentes o futuros — emitir NaN/omitir y alertar.

---

## KPI 5 — Huecos de servicio (conteo)
**Definición**: número de periodos sin vehículos observados **> k × headway programado**.  
**Concepto**  
\[
gap = \mathbb{1}\{t_{sin\_vehículos} > k \cdot headway_{prog}\}
\]
acumulado en la ventana.  
**Unidades**: entero.  
**Métrica**: `pt_service_gaps_count{route_id}`.  
**Parámetros**: por defecto \(k=2\) (`service_gap_factor`) y un piso `service_gap_min_headway_s`.  
**Casos borde**: horas fuera de servicio — usar calendario para evitar falsos positivos.

---

## KPI 6 — Ocupación (ratio, si disponible)
**Definición**: nivel de ocupación 0..1.  
**Cálculo**:  
- Si hay `occupancy_percentage`, usar 0..1 (o convertir 0–100%).  
- Si solo hay `occupancy_status`, mapear a ratio (p. ej., `MANY_SEATS_AVAILABLE` ≈ 0.2, `FEW_SEATS_AVAILABLE` ≈ 0.8, `FULL` = 1.0).  
**Métrica**: `pt_occupancy_ratio{route_id}`  (o por vehículo si aplica).  
**Supuestos**: no emitir cuando no exista dato.  
**Casos borde**: convenciones distintas entre agencias; muestreo esporádico.

---

## Calidad de datos y validación
- Reloj sincronizado (NTP); identificadores estables (`route_id`, `stop_id`).
- Reportar `sample_size` cuando sea bajo.
- Validar OTP/Demora por franja horaria; headways en puntos de control definidos.
- Mantener nombres de **vistas** estables para paneles de Grafana.
