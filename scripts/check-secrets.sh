#!/bin/bash
# Secret Scanner for Infobús Data Repository
# This script checks for exposed secrets and sensitive information

# Note: Not using set -e to ensure script continues even if issues are found

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_FILE="$REPO_ROOT/secret-scan-report.txt"

echo -e "${BLUE}🔍 Secret Scanner for Infobús Data${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""

# Initialize report
echo "Secret Scan Report - $(date)" > "$REPORT_FILE"
echo "======================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

ISSUES_FOUND=0

# Function to log issues
log_issue() {
    local level="$1"
    local message="$2"
    local file="$3"
    local line="$4"
    
    if [ "$level" = "CRITICAL" ]; then
        echo -e "${RED}❌ CRITICAL: $message${NC}"
        ((ISSUES_FOUND++))
    elif [ "$level" = "WARNING" ]; then
        echo -e "${YELLOW}⚠️  WARNING: $message${NC}"
    elif [ "$level" = "INFO" ]; then
        echo -e "${BLUE}ℹ️  INFO: $message${NC}"
    fi
    
    echo "[$level] $message" >> "$REPORT_FILE"
    if [ -n "$file" ]; then
        echo "  File: $file" >> "$REPORT_FILE"
        if [ -n "$line" ]; then
            echo "  Line: $line" >> "$REPORT_FILE"
        fi
    fi
    echo "" >> "$REPORT_FILE"
}

# Function to check if file is tracked in git
is_tracked() {
    local file="$1"
    git ls-files --error-unmatch "$file" >/dev/null 2>&1
}

# Function to check if file should be ignored (check gitignore patterns)
should_be_ignored() {
    local file="$1"
    # Check if the file matches any gitignore pattern
    grep -qE "^\.?${file}$|^\.?${file}\s|/${file}$|/${file}\s" .gitignore 2>/dev/null
}

echo -e "${YELLOW}Checking environment files...${NC}"

# Check for tracked files that should be ignored
for env_file in .env.local .env.prod.local .env.production; do
    if [ -f "$REPO_ROOT/$env_file" ]; then
        if is_tracked "$env_file"; then
            if should_be_ignored "$env_file"; then
                log_issue "CRITICAL" "File '$env_file' is tracked in git but listed in .gitignore (likely contains secrets)" "$env_file"
                log_issue "CRITICAL" "This file should be removed from git tracking with: git rm --cached $env_file" "$env_file"
            else
                log_issue "WARNING" "File '$env_file' is tracked in git and not in .gitignore" "$env_file"
            fi
        else
            if should_be_ignored "$env_file"; then
                log_issue "INFO" "File '$env_file' exists and is properly not tracked (in .gitignore)" "$env_file"
            else
                log_issue "WARNING" "File '$env_file' exists but not in .gitignore - add it to prevent accidental commits" "$env_file"
            fi
        fi
    fi
done

echo -e "${YELLOW}Scanning for Django secret keys...${NC}"

# Check for Django secret keys in tracked files
secret_patterns=(
    "django-insecure-[a-zA-Z0-9@#$%^&*()_+-=!]{40,}"
    "SECRET_KEY\s*=\s*['\"]django-insecure-[^'\"]+['\"]"
    "SECRET_KEY\s*=\s*['\"][^'\"]{40,}['\"]"
)

for pattern in "${secret_patterns[@]}"; do
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            line_num=1
            while IFS= read -r line; do
                if echo "$line" | grep -qE "$pattern"; then
                    # Skip if it's obviously a placeholder
                    if echo "$line" | grep -qE "(CHANGE|PLACEHOLDER|EXAMPLE|DEFAULT|TEMPLATE)"; then
                        log_issue "INFO" "Found placeholder secret pattern (safe)" "$file" "$line_num"
                    else
                        log_issue "CRITICAL" "Found potential real secret key in tracked file" "$file" "$line_num"
                        echo "  Content: $(echo "$line" | sed 's/SECRET_KEY=.*/SECRET_KEY=***REDACTED***/')" >> "$REPORT_FILE"
                    fi
                fi
                ((line_num++))
            done < "$file" 2>/dev/null || true
        fi
    done < <(git ls-files 2>/dev/null | grep -E '\.(py|sh|yml|yaml|env|conf|config)$' || true)
done

echo -e "${YELLOW}Checking for database credentials...${NC}"

# Check for hardcoded database passwords
db_patterns=(
    "password\s*=\s*['\"][^'\"]{3,}['\"]"
    "PASSWORD\s*=\s*['\"][^'\"]{3,}['\"]"
    "DB_PASSWORD\s*=\s*['\"]?[^'\"\\s]{3,}['\"]?"
)

for pattern in "${db_patterns[@]}"; do
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            line_num=1
            while IFS= read -r line; do
                if echo "$line" | grep -qE "$pattern"; then
                    # Skip obvious placeholders
                    if echo "$line" | grep -qE "(CHANGE|PLACEHOLDER|EXAMPLE|DEFAULT|TEMPLATE|postgres|password|secret)"; then
                        log_issue "INFO" "Found placeholder database credential (safe)" "$file" "$line_num"
                    else
                        log_issue "WARNING" "Found potential database credential" "$file" "$line_num"
                    fi
                fi
                ((line_num++))
            done < "$file"
        fi
    done < <(git ls-files | grep -E '\.(py|sh|yml|yaml|env|conf|config)$')
done

echo -e "${YELLOW}Checking git history for secrets...${NC}"

# Check if secrets were committed in the past
if git log --all --grep="secret" --grep="password" --grep="key" --oneline | head -5 | grep -q .; then
    log_issue "WARNING" "Found commits in git history that mention secrets/passwords/keys"
    git log --all --grep="secret" --grep="password" --grep="key" --oneline | head -5 >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
fi

echo -e "${YELLOW}Checking for API keys and tokens...${NC}"

# Check for API keys and tokens
api_patterns=(
    "[A-Za-z0-9]{32,}"  # Generic long strings that might be keys
    "api_key\s*=\s*['\"][^'\"]{10,}['\"]"
    "token\s*=\s*['\"][^'\"]{10,}['\"]"
    "ACCESS_TOKEN\s*=\s*['\"][^'\"]{10,}['\"]"
)

for pattern in "${api_patterns[@]}"; do
    while IFS= read -r file; do
        if [ -f "$file" ] && [[ ! "$file" =~ \.(lock|log)$ ]]; then
            line_num=1
            while IFS= read -r line; do
                if echo "$line" | grep -qE "$pattern"; then
                    # Skip comments and obvious placeholders
                    if echo "$line" | grep -qE "^[[:space:]]*#" || echo "$line" | grep -qE "(CHANGE|PLACEHOLDER|EXAMPLE|DEFAULT|TEMPLATE|your-|xxx|yyy)"; then
                        continue
                    else
                        # Only report if it looks suspicious
                        if echo "$line" | grep -qE "(api_key|token|ACCESS_TOKEN)"; then
                            log_issue "WARNING" "Found potential API key or token" "$file" "$line_num"
                        fi
                    fi
                fi
                ((line_num++))
            done < "$file"
        fi
    done < <(git ls-files | grep -E '\.(py|sh|yml|yaml|env|conf|config)$')
done

echo ""
echo -e "${BLUE}Security recommendations:${NC}"
echo "1. Never commit real secrets to git"
echo "2. Use .env.local for development secrets (ensure it's in .gitignore)"
echo "3. Use environment variables or secret managers in production"
echo "4. Regularly scan for secrets before committing"
echo "5. Consider using pre-commit hooks for secret detection"

# Generate summary
echo "" >> "$REPORT_FILE"
echo "SUMMARY:" >> "$REPORT_FILE"
echo "========" >> "$REPORT_FILE"
echo "Issues found: $ISSUES_FOUND" >> "$REPORT_FILE"
echo "Report saved to: $REPORT_FILE" >> "$REPORT_FILE"

echo ""
if [ $ISSUES_FOUND -gt 0 ]; then
    echo -e "${RED}❌ Found $ISSUES_FOUND critical security issues that need attention!${NC}"
    echo -e "${YELLOW}📋 Detailed report saved to: $REPORT_FILE${NC}"
    echo ""
    echo -e "${BLUE}🔧 Recommended actions:${NC}"
    if [ -f "$REPO_ROOT/.env.local" ] && is_tracked ".env.local"; then
        echo "1. Remove .env.local from git tracking: git rm --cached .env.local"
        echo "2. Verify .env.local is in .gitignore (already done)"
        echo "3. Copy .env.local.example to .env.local for local development"
        echo "4. Generate a new SECRET_KEY for production"
    fi
    exit 1
else
    echo -e "${GREEN}✅ No critical security issues found!${NC}"
    echo -e "${YELLOW}📋 Report saved to: $REPORT_FILE${NC}"
    exit 0
fi