# Grafana Dashboards - Infobús Data

Este documento explica cómo usar Grafana para visualizar los KPIs de tránsito calculados por Celery.

## 🚀 Acceso Rápido

- **URL**: http://localhost:3000
- **Usuario**: `admin`
- **Contraseña**: `admin`

## 📊 Dashboards Disponibles

### Transit KPIs Overview

Dashboard principal que muestra todos los KPIs importantes:

1. **On-Time Performance by Route** (Gauge)
   - Porcentaje de llegadas a tiempo por ruta
   - Verde: >85%, Naranja: 70-85%, Rojo: <70%

2. **Average Delay Over Time** (Time Series)
   - Delay promedio en segundos por ruta
   - Muestra tendencias en las últimas 6 horas

3. **Headway Adherence Ratio** (Time Series)
   - Ratio de headway observado vs programado
   - Valores cercanos a 1.0 indican buen cumplimiento

4. **Feed Freshness (GTFS-RT)** (Time Series)
   - Antigüedad de los datos GTFS-RT en segundos
   - Amarillo: >60s, Rojo: >120s

5. **Service Gaps by Route & Stop** (Table)
   - Gaps de servicio detectados
   - Color de fondo indica severidad

## 🔧 Configuración

### Datasource

Grafana está configurado automáticamente con:
- **Tipo**: PostgreSQL
- **Base de datos**: `infobus_data`
- **Host**: `db:5432`
- **Usuario**: `postgres`

La configuración se encuentra en `grafana/provisioning/datasources/datasource.yml`

### Dashboards

Los dashboards se cargan automáticamente desde `grafana/dashboards/`

Para agregar o modificar dashboards:
1. Edita los archivos JSON en `grafana/dashboards/`
2. O usa la UI de Grafana y exporta el JSON

## 📈 Queries SQL de Ejemplo

### OTP por Ruta (últimas 24 horas)

```sql
SELECT 
  window_start AS time,
  route_id,
  otp_percentage
FROM kpi_on_time_performance
WHERE window_start >= NOW() - INTERVAL '24 hours'
ORDER BY window_start;
```

### Delay Promedio por Hora del Día

```sql
SELECT 
  EXTRACT(HOUR FROM window_start) AS hour,
  route_id,
  AVG(average_delay_s) AS avg_delay
FROM kpi_average_delay
WHERE window_start >= NOW() - INTERVAL '7 days'
GROUP BY hour, route_id
ORDER BY hour, route_id;
```

### Headway Adherence por Parada

```sql
SELECT 
  window_start AS time,
  route_id,
  stop_id,
  adherence_ratio
FROM kpi_headway_adherence
WHERE window_start >= NOW() - INTERVAL '24 hours'
  AND stop_id = 'STOP_A'
ORDER BY window_start;
```

## 🔄 Auto-Refresh

Los dashboards están configurados para actualizar automáticamente cada 30 segundos. Puedes cambiar esto en la esquina superior derecha de cada dashboard.

## 🎨 Personalización

### Cambiar el Tema

1. Ve a **Profile** (ícono de usuario) → **Preferences**
2. Cambia **UI Theme** a Light o Dark

### Crear Alertas

Grafana soporta alertas basadas en umbrales:

1. Edita un panel
2. Ve a la pestaña **Alert**
3. Configura condiciones (ej: OTP < 70%)
4. Configura notificaciones (email, Slack, etc.)

### Variables de Dashboard

Puedes agregar variables para filtrar por ruta o parada:

1. Dashboard Settings → Variables → Add variable
2. Tipo: Query
3. Query: `SELECT DISTINCT route_id FROM kpi_on_time_performance ORDER BY route_id`

## 📊 Estructura de Datos

### Tablas KPI Principales

- `kpi_on_time_performance` - OTP por ruta y ventana de tiempo
- `kpi_average_delay` - Delay promedio por ruta
- `kpi_headway_adherence` - Adherencia de headway por ruta/parada
- `kpi_feed_freshness` - Freshness de feeds GTFS-RT
- `kpi_service_gaps` - Gaps de servicio detectados
- `kpi_occupancy` - Ocupación promedio por ruta

Todas las tablas tienen:
- `window_start`, `window_end` - Ventana temporal del KPI
- `created_at`, `updated_at` - Timestamps de auditoría

## 🔌 Plugins Recomendados

Grafana viene con plugins preinstalados, pero puedes agregar más:

```bash
# En el docker-compose.yml, agrega a la variable de entorno:
GF_INSTALL_PLUGINS=grafana-piechart-panel,grafana-worldmap-panel
```

## 🚨 Troubleshooting

### Dashboard no muestra datos

1. Verifica que los Celery tasks estén corriendo:
   ```bash
   docker compose logs -f celery-worker
   ```

2. Verifica que haya datos recientes:
   ```bash
   docker compose exec db psql -U postgres -d infobus_data -c "SELECT COUNT(*) FROM kpi_on_time_performance WHERE window_start >= NOW() - INTERVAL '1 hour';"
   ```

3. Regenera datos mock si es necesario:
   ```bash
   docker compose exec web uv run python scripts/populate_mock_data.py
   ```

### Datasource connection error

Verifica que PostgreSQL esté corriendo:
```bash
docker compose ps db
```

Reinicia Grafana:
```bash
docker compose restart grafana
```

## 📚 Recursos

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [PostgreSQL Data Source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/best-practices-for-creating-dashboards/)

## 🎯 Próximos Pasos

1. **Agregar alertas** para KPIs críticos (OTP < 70%, Delay > 300s)
2. **Crear dashboard por ruta** con drill-down a stops específicos
3. **Integrar con notificaciones** (Slack, email) para alertas
4. **Agregar análisis comparativos** (día vs día, semana vs semana)
5. **Crear dashboard ejecutivo** con métricas de alto nivel
