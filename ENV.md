# Environment Variables Configuration

This project uses a simplified environment configuration structure with three files:

## 📁 **File Structure**

### `.env` (tracked in git)
- **Contains**: Default/shared variables that work for both development and production
- **Purpose**: Base configuration that all environments can build upon
- **Security**: No sensitive data (secrets use placeholder values)
- **Git**: ✅ Tracked in version control

### `.env.local` (git-ignored)  
- **Contains**: Personal development overrides and secrets
- **Purpose**: Local development customization and real SECRET_KEY
- **Security**: Contains actual secrets and personal settings
- **Git**: ❌ Never committed (in .gitignore)
- **Template**: Copy from `.env.local.example` to get started

### `.env.prod` (tracked in git)
- **Contains**: Production-specific overrides only
- **Purpose**: Production settings that override defaults from `.env`
- **Security**: Contains production placeholders (change before deploying)
- **Git**: ✅ Tracked in version control

## 🔧 **How It Works**

### Development Mode
```bash
# Docker Compose automatically loads in this order:
# 1. .env (base configuration)
# 2. .env.local (your personal overrides)

./scripts/dev.sh
```

### Production Mode  
```bash
# Explicitly load production overrides:
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d
```

## 🚀 **Getting Started**

1. **Create your local environment file:**
   ```bash
   cp .env.local.example .env.local
   ```

2. **Generate a secret key:**
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

3. **Update `.env.local` with your secret key:**
   ```bash
   SECRET_KEY=your-generated-secret-key-here
   DEBUG=True
   ```

4. **Start development:**
   ```bash
   ./scripts/dev.sh
   ```

## 🔒 **Security Best Practices**

- ✅ `.env` contains only non-sensitive defaults
- ✅ `.env.local` is git-ignored and contains real secrets  
- ✅ `.env.prod` has placeholder values for production deployment
- ✅ Production secrets should be managed separately (environment variables, secret managers, etc.)

## 📋 **Migration from Old Structure**

The old setup had:
- ❌ `.env` with mixed dev/prod settings and real secrets
- ❌ `.env.dev` with redundant configuration  
- ❌ `.env.prod` with full configuration duplication

The new setup eliminates redundancy and improves security by:
- ✅ Clear separation of concerns
- ✅ No secrets in tracked files
- ✅ Single source of truth for shared settings
- ✅ Easy local customization without affecting others
