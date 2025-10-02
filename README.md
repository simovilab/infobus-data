# Infobús Data

## 🚀 Quick Start

1. **Setup environment variables:**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your SECRET_KEY (see ENV.md for details)
   ```

2. **Start development environment:**
   ```bash
   ./scripts/dev.sh
   ```

3. **Access the application:**
   - Website: http://localhost:8000
   - Admin: http://localhost:8000/admin (admin/admin)
   - Health: http://localhost:8000/health/

## 📚 Documentation

- [Environment Configuration](ENV.md) - Environment variables setup
- [Docker Setup](DOCKER.md) - Docker configuration details
- [Production Deployment](PRODUCTION.md) - Production deployment guide
- [`KPI Dictionary`](kpi_dictionary_en.md) - Definitions, formulas, assumptions, and edge cases for KPIs
- [`Diccionario de KPIs`](kpi_dictionary_es.md) - Definiciones, fórmulas, supuestos y casos borde de los KPIs.

## 🛠️ Development

### Local Commands
```bash
# View logs
docker compose logs -f

# Stop environment
docker compose down

# Restart web service (after code changes)
docker compose restart web
```

### Celery Commands (if running locally)
```bash
celery -A infobus_data worker --loglevel=info
celery -A infobus_data beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --loglevel=info
```

## 🏗️ Architecture

- **Django** with Channels (ASGI)
- **PostgreSQL** with PostGIS
- **Redis** for caching and Celery
- **Celery** for background tasks
- **Docker** for containerization
- **Nginx** for production reverse proxy
