#!/bin/bash
# Production environment startup script

echo "🏭 Starting Infobús Data in PRODUCTION mode..."
echo "Features enabled:"
echo "  - Nginx reverse proxy"
echo "  - Daphne ASGI server"
echo "  - Django Channels support"
echo "  - Static file caching"
echo "  - Security headers"
echo "  - Rate limiting"
echo "  - Optimized for performance"
echo ""

# Check if .env.prod exists
if [ ! -f ".env.prod" ]; then
    echo "❌ Error: .env.prod file not found!"
    echo "Please create .env.prod with your production settings."
    echo "You can copy from .env.prod template and modify the values."
    exit 1
fi

# Check if production SECRET_KEY is still default
if grep -q "django-insecure-CHANGE-THIS-IN-PRODUCTION" .env.prod; then
    echo "⚠️  WARNING: You're using the default SECRET_KEY!"
    echo "Please generate a secure SECRET_KEY for production."
    echo "You can use: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "🔧 Building production images..."

# Use production configuration
export COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
docker compose --profile production --env-file .env.prod up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "🏥 Checking service health..."
if curl -s http://localhost/health/ > /dev/null; then
    echo "✅ Production environment started successfully!"
else
    echo "⚠️  Services started but health check failed. Check logs for details."
fi

echo ""
echo "🌐 Website: http://localhost (Nginx)"
echo "🔧 Admin: http://localhost/admin"
echo "🏥 Health: http://localhost/health/"
echo "💾 Database: localhost:5432"
echo "🔄 Redis: localhost:6379"
echo ""
echo "📊 Production monitoring:"
echo "  - Check health: curl http://localhost/health/"
echo "  - View Nginx logs: docker compose --profile production --env-file .env.prod logs nginx"
echo "  - View app logs: docker compose --profile production --env-file .env.prod logs web"
echo "  - View all logs: docker compose --profile production --env-file .env.prod logs -f"
echo ""
echo "🛑 To stop: docker compose --profile production --env-file .env.prod down"
