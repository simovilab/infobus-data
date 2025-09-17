# Secret Scanning and Security Guide

This guide explains how to check for exposed secrets in the Infobús Data repository and maintain security best practices.

## 🔍 Quick Secret Check

Run the built-in secret scanner:

```bash
./scripts/check-secrets.sh
```

This script will:
- ✅ Check for environment files that shouldn't be tracked in git
- ✅ Scan for Django secret keys in tracked files
- ✅ Look for database credentials
- ✅ Search for API keys and tokens
- ✅ Generate a detailed report

## 🚨 Common Security Issues

### 1. Environment Files Tracked in Git

**Problem**: Files like `.env.local` containing real secrets are committed to git.

**Solution**:
```bash
# Remove from git tracking (keeps local file)
git rm --cached .env.local

# Ensure it's in .gitignore
echo ".env.local" >> .gitignore
```

### 2. Django Secret Keys in Code

**Problem**: Real Django SECRET_KEY values in tracked files.

**Example of UNSAFE code**:
```python
SECRET_KEY = "django-insecure-c@$&_-538y3tc11!1bp+^i(r&#g^y%-wns1aallk(q_or9j6(x"
```

**Safe approach**:
```python
SECRET_KEY = config("SECRET_KEY")  # Load from environment
```

### 3. Database Credentials

**Problem**: Hardcoded passwords in configuration files.

**Safe approach**: Use environment variables or placeholder values in tracked files.

## 🛡️ Security Best Practices

### Environment File Structure

- **`.env`** - Default values, safe to track (no real secrets)
- **`.env.local`** - Local development secrets, **NEVER track in git**
- **`.env.prod`** - Production overrides with placeholders, safe to track
- **`.env.local.example`** - Template file, safe to track

### Secret Management Guidelines

1. **Never commit real secrets** to version control
2. **Use environment variables** for all sensitive data
3. **Use placeholder values** in tracked configuration files
4. **Generate unique secrets** for each environment
5. **Rotate secrets regularly**, especially after team changes

## 🔧 Manual Secret Detection

### Find Django Secret Keys
```bash
grep -r "django-insecure-" --exclude-dir=.git .
```

### Find Environment Files
```bash
find . -name "*.env*" -type f | grep -v .git
```

### Check What's Tracked in Git
```bash
git ls-files | grep -E "\.(env|key|secret)"
```

### Search for Potential Secrets
```bash
grep -r "SECRET_KEY\|password\|api_key" --include="*.py" --include="*.yml" .
```

## 🚀 Fixing Exposed Secrets

If you find exposed secrets:

### Step 1: Remove from Git Tracking
```bash
# Remove file from git but keep locally
git rm --cached path/to/secret-file

# Add to .gitignore
echo "path/to/secret-file" >> .gitignore
```

### Step 2: Generate New Secrets
```bash
# For Django SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# For database passwords
openssl rand -base64 32
```

### Step 3: Update Environment Files
1. Update `.env.local` with new secrets
2. Update production environment with new secrets
3. Ensure tracked files only have placeholder values

### Step 4: Commit the Changes
```bash
git add .gitignore
git commit -m "security: remove exposed secrets and update gitignore"
```

## 📋 Pre-commit Checks

Add these checks to your workflow:

### Before Each Commit
```bash
# Run secret scanner
./scripts/check-secrets.sh

# Check what you're about to commit
git diff --cached --name-only | grep -E "\.(env|secret|key)"
```

### Git Hooks (Optional)

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
echo "🔍 Checking for secrets..."
./scripts/check-secrets.sh
if [ $? -ne 0 ]; then
    echo "❌ Secret check failed. Commit aborted."
    exit 1
fi
```

## 🔄 Regular Security Audits

### Weekly Checks
- Run `./scripts/check-secrets.sh`
- Review environment file access logs
- Check for new team members who need secret access

### After Team Changes
- Rotate shared secrets
- Review access to production environments
- Update `.env.local.example` if needed

## 📞 Emergency Response

If secrets are exposed in git history:

1. **Immediately rotate** all exposed secrets
2. **Force push** cleaned history (if possible and safe)
3. **Notify team members** to update their local environments
4. **Review access logs** for potential unauthorized access

## 🛠️ Tools and Resources

- **Secret Scanner**: `./scripts/check-secrets.sh` (built-in)
- **Django Secret Generator**: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- **Environment Guide**: See `ENV.md` for detailed environment setup
- **Production Guide**: See `PRODUCTION.md` for production security checklist

## ❓ FAQ

**Q: I accidentally committed a secret. What do I do?**
A: 1) Immediately rotate the secret, 2) Remove it from git tracking, 3) Add to .gitignore, 4) Commit the fix.

**Q: How often should I run the secret scanner?**
A: Before every commit, and weekly as part of regular maintenance.

**Q: Can I automate secret checking?**
A: Yes, use git hooks or CI/CD pipeline checks to run `./scripts/check-secrets.sh` automatically.

**Q: What if the scanner reports false positives?**
A: Review the report in `secret-scan-report.txt` and update the script patterns if needed.

---

> 🔒 **Remember**: When in doubt, don't commit it. It's easier to prevent secret exposure than to clean it up afterward.