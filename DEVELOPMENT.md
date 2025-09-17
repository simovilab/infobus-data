# Development Instructions

## Docker Compose File Structure

This project uses multiple Docker Compose files:

- `docker-compose.yml` - Development configuration
- `docker-compose.production.yml` - Production configuration

## Running Development Environment

To avoid conflicts and ensure proper environment variable precedence, always specify the exact compose file:

```bash
# Start development environment
docker compose -f docker-compose.yml up

# Or specific services
docker compose -f docker-compose.yml up web -d

# Check configuration
docker compose -f docker-compose.yml config web

# Execute commands in development containers
docker compose -f docker-compose.yml exec web bash
```

## Running Production Environment

```bash
# Start production environment with Nginx
docker compose -f docker-compose.production.yml --profile production up -d

# Check production services status
docker compose -f docker-compose.production.yml ps

# View production logs
docker compose -f docker-compose.production.yml logs -f

# Stop production environment
docker compose -f docker-compose.production.yml down
```

### Production Environment Details

- **Web Server**: Nginx (port 80) with reverse proxy to Django
- **Django**: Runs with Daphne ASGI server (internal port 8000)
- **Static Files**: Served by Nginx with aggressive caching headers
- **Environment**: `DEBUG=False`, optimized for production
- **Services**: PostgreSQL, Redis, Django web, Celery worker, Celery beat, Nginx

## Environment Variables

The development environment loads environment variables in this order:
1. `.env` (base configuration)
2. `.env.dev` (development overrides)
3. `.env.local` (personal overrides, git-ignored)

Key development settings in `.env.dev`:
- `DEBUG=True` - Enables Django debug mode
- `DJANGO_SERVE_STATIC=True` - Enables static file serving
- `LOG_LEVEL=DEBUG` - Verbose logging

## Static Files in Development

Static files are automatically collected and served by Django when:
- `DEBUG=True` OR `DJANGO_SERVE_STATIC=True`

The URL configuration includes custom static file serving that works even when `DEBUG=False`.

## Troubleshooting

If static files aren't loading in development:

1. Ensure you're using the correct compose file: `docker compose -f docker-compose.yml`
2. Check environment variables: `docker compose -f docker-compose.yml exec web env | grep DEBUG`
3. Manually collect static files: `docker compose -f docker-compose.yml exec web uv run python manage.py collectstatic`
