#!/bin/bash

# ============================================================================
# Quick Deploy: Storage Migrations Only (007-016)
# ============================================================================
# Purpose: Deploy just the storage infrastructure needed for Worker 4 testing
# Time: ~2 minutes
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Database connection
DB_HOST="${DB_HOST:-db.vzsohavtuotocgrfkfyd.supabase.co}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw}"

export PGPASSWORD="$DB_PASSWORD"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deploy Storage Migrations (007-016)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check psql
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ psql not found${NC}"
    echo "Install: brew install postgresql (Mac) or sudo apt install postgresql-client (Linux)"
    exit 1
fi

# Test connection
echo -e "${YELLOW}🔍 Testing connection...${NC}"
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ Connection failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Connected${NC}"
echo ""

# Storage migrations
MIGRATIONS=(
    "supabase/migrations/20250101000007_create_storage_buckets.sql"
    "supabase/migrations/20250101000008_storage_helper_functions.sql"
    "supabase/migrations/20250101000009_storage_objects_rls.sql"
    "supabase/migrations/20250101000010_documents_metadata_rls.sql"
    "supabase/migrations/20250101000011_add_system_path_to_documents.sql"
    "supabase/migrations/20250101000012_role_directory_permissions.sql"
    "supabase/migrations/20250101000013_hierarchical_storage_functions.sql"
    "supabase/migrations/20250101000014_update_storage_rls_directory_permissions.sql"
    "supabase/migrations/20250101000015_update_documents_rls_directory_permissions.sql"
    "supabase/migrations/20250101000016_remove_mime_restrictions.sql"
)

NAMES=(
    "Create storage buckets (documents, raw-uploads)"
    "Storage helper functions (path validation)"
    "Storage RLS policies (bucket access)"
    "Documents metadata RLS (table access)"
    "Add system_path column to documents"
    "Create role_directory_permissions table"
    "Hierarchical storage functions (permissions)"
    "Update storage RLS (directory-aware)"
    "Update documents RLS (directory-aware)"
    "Remove MIME type restrictions"
)

TOTAL=${#MIGRATIONS[@]}
SUCCESS=0
FAILED=0

for i in "${!MIGRATIONS[@]}"; do
    MIGRATION="${MIGRATIONS[$i]}"
    NAME="${NAMES[$i]}"
    NUM=$((i + 1))

    echo -e "${YELLOW}[$NUM/$TOTAL] ${NAME}${NC}"

    if [ ! -f "$MIGRATION" ]; then
        echo -e "${RED}❌ File not found: $MIGRATION${NC}"
        FAILED=$((FAILED + 1))
        continue
    fi

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION" > /tmp/migration_${i}.log 2>&1; then
        echo -e "${GREEN}✅ Success${NC}"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "${RED}❌ Failed${NC}"
        cat /tmp/migration_${i}.log | head -10
        FAILED=$((FAILED + 1))
    fi

    echo ""
done

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total: $TOTAL"
echo -e "${GREEN}Success: $SUCCESS${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
fi
echo ""

# Verification
if [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}🔍 Verifying deployment...${NC}"

    # Check system_path column
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='documents' AND column_name='system_path');" \
        | grep -q "t"; then
        echo -e "${GREEN}✅ system_path column exists${NC}"
    else
        echo -e "${RED}❌ system_path column missing${NC}"
    fi

    # Check documents bucket
    BUCKET_CHECK=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM storage.buckets WHERE id='documents';" | tr -d ' ')
    if [ "$BUCKET_CHECK" -eq 1 ]; then
        echo -e "${GREEN}✅ documents bucket exists${NC}"
    else
        echo -e "${RED}❌ documents bucket missing${NC}"
    fi

    # Check MIME restrictions
    MIME_CHECK=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT allowed_mime_types IS NULL FROM storage.buckets WHERE id='documents';" | tr -d ' ')
    if [ "$MIME_CHECK" = "t" ]; then
        echo -e "${GREEN}✅ MIME restrictions removed (all types allowed)${NC}"
    else
        echo -e "${YELLOW}⚠️  MIME restrictions still active${NC}"
    fi

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "Next: Test your Worker 4 upload!"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ DEPLOYMENT INCOMPLETE${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

rm -f /tmp/migration_*.log
exit 0
