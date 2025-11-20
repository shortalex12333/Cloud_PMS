#!/bin/bash

# ============================================================================
# Deploy Hierarchical Storage Migrations
# ============================================================================
# Purpose: Deploy migrations 011-015 for directory-based permissions
# Author: Worker 1 (Supabase Architect)
# Date: 2025-01-01
#
# These migrations add:
# - system_path column to documents table
# - role_directory_permissions table
# - Hierarchical storage helper functions
# - Updated RLS policies for directory permissions
#
# Prerequisites:
# - Migrations 000-010 already deployed
# - psql installed
# - Database credentials in environment
# ============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Database connection details (from supabase_credentials.md)
DB_HOST="${DB_HOST:-db.vzsohavtuotocgrfkfyd.supabase.co}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw}"

export PGPASSWORD="$DB_PASSWORD"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Hierarchical Storage Migration Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ Error: psql not found${NC}"
    echo "Install PostgreSQL client:"
    echo "  Mac: brew install postgresql"
    echo "  Ubuntu: sudo apt install postgresql-client"
    exit 1
fi

# Test connection
echo -e "${YELLOW}🔍 Testing database connection...${NC}"
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Connection successful${NC}"
else
    echo -e "${RED}❌ Connection failed${NC}"
    echo "Check your credentials and network connection"
    exit 1
fi

echo ""

# Migration files
MIGRATIONS=(
    "supabase/migrations/20250101000011_add_system_path_to_documents.sql"
    "supabase/migrations/20250101000012_role_directory_permissions.sql"
    "supabase/migrations/20250101000013_hierarchical_storage_functions.sql"
    "supabase/migrations/20250101000014_update_storage_rls_directory_permissions.sql"
    "supabase/migrations/20250101000015_update_documents_rls_directory_permissions.sql"
)

MIGRATION_NAMES=(
    "Add system_path column"
    "Create role_directory_permissions table"
    "Create hierarchical storage functions"
    "Update storage.objects RLS policies"
    "Update documents table RLS policies"
)

# Deploy each migration
TOTAL=${#MIGRATIONS[@]}
SUCCESS=0
FAILED=0

for i in "${!MIGRATIONS[@]}"; do
    MIGRATION="${MIGRATIONS[$i]}"
    NAME="${MIGRATION_NAMES[$i]}"
    NUM=$((i + 1))

    echo -e "${YELLOW}[$NUM/$TOTAL] Deploying: $NAME${NC}"
    echo -e "${BLUE}File: $MIGRATION${NC}"

    if [ ! -f "$MIGRATION" ]; then
        echo -e "${RED}❌ File not found: $MIGRATION${NC}"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Deploy migration
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION" > /tmp/migration_${i}.log 2>&1; then
        echo -e "${GREEN}✅ Success${NC}"
        SUCCESS=$((SUCCESS + 1))

        # Show NOTICE messages from migration
        if grep -q "NOTICE" /tmp/migration_${i}.log; then
            echo -e "${BLUE}Output:${NC}"
            grep "NOTICE" /tmp/migration_${i}.log | sed 's/NOTICE:  /  /'
        fi
    else
        echo -e "${RED}❌ Failed${NC}"
        echo -e "${RED}Error log:${NC}"
        cat /tmp/migration_${i}.log | head -20
        FAILED=$((FAILED + 1))
    fi

    echo ""
done

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deployment Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total migrations: $TOTAL"
echo -e "${GREEN}Successful: $SUCCESS${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
fi
echo ""

# Verification
if [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}🔍 Running verification checks...${NC}"

    # Check 1: system_path column exists
    echo -e "${BLUE}1. Checking system_path column...${NC}"
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='documents' AND column_name='system_path');" \
        | grep -q "t"; then
        echo -e "${GREEN}   ✅ system_path column exists${NC}"
    else
        echo -e "${RED}   ❌ system_path column missing${NC}"
    fi

    # Check 2: role_directory_permissions table exists
    echo -e "${BLUE}2. Checking role_directory_permissions table...${NC}"
    COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='role_directory_permissions';" | tr -d ' ')
    if [ "$COUNT" -eq 1 ]; then
        echo -e "${GREEN}   ✅ role_directory_permissions table exists${NC}"
    else
        echo -e "${RED}   ❌ role_directory_permissions table missing${NC}"
    fi

    # Check 3: Helper functions exist
    echo -e "${BLUE}3. Checking helper functions...${NC}"
    FUNCS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM pg_proc WHERE proname IN (
            'can_access_storage_path',
            'can_upload_to_storage_path',
            'build_storage_path',
            'get_accessible_directories'
        );" | tr -d ' ')
    if [ "$FUNCS" -eq 4 ]; then
        echo -e "${GREEN}   ✅ All helper functions exist ($FUNCS/4)${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Found $FUNCS/4 helper functions${NC}"
    fi

    # Check 4: Updated RLS policies
    echo -e "${BLUE}4. Checking storage.objects RLS policies...${NC}"
    STORAGE_POLICIES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM pg_policies WHERE schemaname='storage' AND tablename='objects';" | tr -d ' ')
    echo -e "${GREEN}   ✅ Found $STORAGE_POLICIES policies on storage.objects${NC}"

    echo -e "${BLUE}5. Checking documents table RLS policies...${NC}"
    DOC_POLICIES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM pg_policies WHERE schemaname='public' AND tablename='documents';" | tr -d ' ')
    echo -e "${GREEN}   ✅ Found $DOC_POLICIES policies on documents${NC}"

    # Check 6: Sample permissions
    echo -e "${BLUE}6. Checking role_directory_permissions data...${NC}"
    PERM_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM role_directory_permissions;" | tr -d ' ')
    if [ "$PERM_COUNT" -gt 0 ]; then
        echo -e "${GREEN}   ✅ Found $PERM_COUNT permission entries${NC}"
    else
        echo -e "${YELLOW}   ⚠️  No permissions configured yet${NC}"
        echo -e "${YELLOW}      Run SEED_DIRECTORY_PERMISSIONS.sql to add defaults${NC}"
    fi

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Configure role_directory_permissions for each yacht"
    echo "2. Test directory access with different user roles"
    echo "3. Update Worker 5 to include system_path in uploads"
    echo "4. Test end-to-end upload and access flow"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "- Architecture guide: supabase/HIERARCHICAL_STORAGE_ARCHITECTURE.md"
    echo "- Helper functions: Run 'SELECT * FROM get_accessible_directories();' to test"
    echo ""
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ DEPLOYMENT INCOMPLETE${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Some migrations failed. Check error logs above.${NC}"
    echo "Fix errors and re-run this script."
    exit 1
fi

# Clean up temp files
rm -f /tmp/migration_*.log

exit 0
