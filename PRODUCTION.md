# Infobús Data - Production Deployment

This document explains how to deploy Infobús Data in production using Docker Compose with Nginx and Daphne.

## 🏗️ Architecture

The production setup includes:

- **Nginx**: Reverse proxy, static file serving, SSL termination, rate limiting
- **Daphne**: ASGI server for Django with Channels support
- **PostgreSQL**: Database
- **Redis**: Cache and Celery broker
- **Celery Worker**: Background task processing
- **Celery Beat**: Periodic task scheduling

## 🚀 Quick Start

1. **Copy and configure environment file:**

   ```bash
   cp .env.prod .env.prod.local
   # Edit .env.prod.local with your production values
   ```

2. **Generate a secure secret key:**

   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

3. **Update `.env.prod.local` with:**

   - Your generated `SECRET_KEY`
   - Secure database passwords
   - Your domain name in `ALLOWED_HOSTS`
   - SSL settings (when ready)

4. **Start production environment:**
   ```bash
   ./scripts/prod.sh
   ```

## 🔧 Manual Deployment

If you prefer manual control:

```bash
# Build and start services
export COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
docker compose --profile production --env-file .env.prod up --build -d

# Check logs
docker compose --profile production --env-file .env.prod logs -f

# Stop services
docker compose --profile production --env-file .env.prod down
```

## 📊 Monitoring

### Health Checks

```bash
# Application health
curl http://localhost/health/

# Individual services
docker compose --profile production --env-file .env.prod ps
```

### Logs

```bash
# All services
docker compose --profile production --env-file .env.prod logs -f

# Specific services
docker compose --profile production --env-file .env.prod logs nginx
docker compose --profile production --env-file .env.prod logs web
docker compose --profile production --env-file .env.prod logs celery-worker
```

## 🔒 Security Checklist

### Before Going Live:

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Update database passwords
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up SSL certificates
- [ ] Enable HTTPS redirects (`SECURE_SSL_REDIRECT=True`)
- [ ] Enable secure cookies (`SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`)
- [ ] Review and update rate limiting in `nginx/nginx.conf`
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Set up monitoring and alerting

## 🌐 SSL/HTTPS Setup

1. **Obtain SSL certificates** (Let's Encrypt recommended):

   ```bash
   # Using certbot
   sudo apt install certbot
   sudo certbot certonly --standalone -d your-domain.com
   ```

2. **Copy certificates to nginx/ssl directory:**

   ```bash
   cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
   cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
   ```

3. **Update nginx/nginx.conf:**

   - Uncomment HTTPS server block
   - Update server_name with your domain
   - Enable HTTP to HTTPS redirect

4. **Update .env.prod:**
   ```env
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

## 🗄️ Database Management

### Backups

```bash
# Create backup
docker compose --profile production --env-file .env.prod exec db pg_dump -U postgres infobus_data > backup.sql

# Restore backup
docker compose --profile production --env-file .env.prod exec -T db psql -U postgres infobus_data < backup.sql
```

### Migrations

```bash
docker compose --profile production --env-file .env.prod exec web uv run python manage.py migrate
```

## 📈 Performance Optimization

### Nginx Caching

Static files are automatically cached with long expiration times.

### Database Optimization

- Consider connection pooling for high traffic
- Regular database maintenance (VACUUM, ANALYZE)
- Monitor query performance

### Resource Limits

Adjust Docker resource limits in production:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
        reservations:
          memory: 256M
```

## 🚨 Troubleshooting

### Common Issues

1. **Static files not loading:**

   ```bash
   docker compose --profile production --env-file .env.prod exec web uv run python manage.py collectstatic --noinput
   ```

2. **Database connection errors:**

   - Check database service is running
   - Verify connection string in .env.prod
   - Check network connectivity

3. **Nginx errors:**
   ```bash
   docker compose --profile production --env-file .env.prod logs nginx
   ```

### Getting Help

- Check application logs: `docker compose --profile production --env-file .env.prod logs web`
- Verify health endpoint: `curl http://localhost/health/`
- Check service status: `docker compose --profile production --env-file .env.prod ps`

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
./scripts/prod.sh

# Run migrations if needed
docker compose --profile production --env-file .env.prod exec web uv run python manage.py migrate
```

### Regular Maintenance

- Monitor disk space
- Review and rotate logs
- Update dependencies regularly
- Monitor SSL certificate expiration
- Regular security audits
