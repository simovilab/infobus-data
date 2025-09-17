#!/bin/bash
# Development environment startup script

echo "🚀 Starting Infobús Data in DEVELOPMENT mode..."
echo "Features enabled:"
echo "  - Live reloading"
echo "  - Debug mode"
echo "  - Volume mounting for code changes"
echo "  - Django development server"
echo ""

# Use the base docker-compose.yml which is configured for development
# Docker Compose will automatically load .env and then .env.local
docker compose up --build -d

echo ""
echo "✅ Development environment started!"
echo "🌐 Website: http://localhost:8000"
echo "🔧 Admin: http://localhost:8000/admin (admin/admin)"
echo "💾 Database: localhost:5432 (postgres/postgres)"
echo "🔄 Redis: localhost:6379"
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
