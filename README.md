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
   - Grafana: http://localhost:3000 (admin/admin)

## 📚 Documentation

- [Environment Configuration](ENV.md) - Environment variables setup
- [Docker Setup](DOCKER.md) - Docker configuration details
- [Production Deployment](PRODUCTION.md) - Production deployment guide
- [Grafana Dashboards](GRAFANA.md) - KPI visualization and monitoring

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
- **PostgreSQL** with TimescaleDB extension
- **Redis** for caching and Celery
- **Celery** for background KPI computation
- **Grafana** for KPI visualization
- **Docker** for containerization
- **Nginx** for production reverse proxy
