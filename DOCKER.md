# Infobús Data - Docker Setup

This document explains how to run the Infobús Data application using Docker.

## Quick Start

1. **Clone and setup environment:**

   ```bash
   # Copy environment file
   cp .env.example .env

   # Edit .env with your configuration
   nano .env
   ```

2. **Build and run with Docker Compose:**

   ```bash
   # Development mode
   docker-compose up --build

   # Production mode (with Nginx)
   docker-compose --profile production up --build
   ```

3. **Access the application:**
   - Django app: http://localhost:8000
   - Admin interface: http://localhost:8000/admin (admin/admin)
   - With Nginx: http://localhost

## Services

The Docker setup includes these services:

- **web**: Django application with Daphne ASGI server
- **db**: PostgreSQL 16 database
- **redis**: Redis for Celery and Django Channels
- **celery-worker**: Celery worker for background tasks
- **celery-beat**: Celery Beat scheduler
- **nginx**: Nginx reverse proxy (production profile only)

## Development Workflow

### Running for Development

```bash
# Start all services
docker-compose up

# Start specific services
docker-compose up db redis

# Run Django development server locally
uv run python manage.py runserver
```

### Database Operations

```bash
# Run migrations
docker-compose exec web uv run python manage.py migrate

# Create superuser
docker-compose exec web uv run python manage.py createsuperuser

# Access PostgreSQL
docker-compose exec db psql -U postgres -d Infobús_data
```

### Celery Operations

```bash
# View celery worker logs
docker-compose logs -f celery-worker

# View celery beat logs
docker-compose logs -f celery-beat

# Monitor tasks
docker-compose exec celery-worker uv run celery -A Infobús_data events
```

## Production Deployment

### With Nginx (Recommended)

```bash
# Build and start with production profile
docker-compose --profile production up --build -d

# View logs
docker-compose logs -f web nginx
```

### Environment Variables

Key environment variables for production:

```env
DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@host:port/dbname
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### SSL/HTTPS Setup

For production with SSL, modify `nginx.conf` to include:

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/private.key;
    # ... rest of configuration
}
```

## Data Persistence

The following Docker volumes persist data:

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis data
- `static_volume`: Django static files
- `media_volume`: Django media files
- `celery_beat_data`: Celery Beat schedule

## Monitoring

### Health Checks

The setup includes health checks for:

- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`

### Logs

```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f web
docker-compose logs -f celery-worker

# View last 100 lines
docker-compose logs --tail=100 web
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if database is ready
docker-compose exec web uv run python manage.py dbshell

# Restart database service
docker-compose restart db
```

### Celery Issues

```bash
# Restart celery services
docker-compose restart celery-worker celery-beat

# Check Redis connection
docker-compose exec redis redis-cli ping
```

### Build Issues

```bash
# Force rebuild without cache
docker-compose build --no-cache

# Remove all containers and volumes
docker-compose down -v
docker system prune -a
```

## Commands Reference

```bash
# Build services
docker-compose build

# Start services in background
docker-compose up -d

# Stop services
docker-compose down

# View running services
docker-compose ps

# Execute commands in service
docker-compose exec web bash

# View service logs
docker-compose logs service-name

# Scale services
docker-compose up --scale celery-worker=3
```
