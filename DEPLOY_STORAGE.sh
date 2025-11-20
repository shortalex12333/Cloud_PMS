#!/bin/bash
# ============================================================================
# Quick Deploy Script for Storage Migrations
# ============================================================================
# This script deploys storage migrations (007-010) to Supabase
# Run from project root: bash DEPLOY_STORAGE.sh
# ============================================================================

set -e  # Exit on error

echo "========================================="
echo "CelesteOS Storage Migrations Deployment"
echo "========================================="
echo ""

# Database credentials
export PGPASSWORD='PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw'
DB_HOST='db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT='5432'
DB_USER='postgres'
DB_NAME='postgres'

echo "Testing connection..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "❌ Connection failed. Check credentials."
  exit 1
fi

echo "✅ Connection successful"
echo ""

# Option 1: Deploy individual migrations
if [ "$1" == "individual" ]; then
  echo "Deploying migrations individually..."

  echo "[1/4] Migration 007: Storage Buckets"
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -f supabase/migrations/20250101000007_create_storage_buckets.sql

  echo "[2/4] Migration 008: Helper Functions"
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -f supabase/migrations/20250101000008_storage_helper_functions.sql

  echo "[3/4] Migration 009: Storage RLS"
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -f supabase/migrations/20250101000009_storage_objects_rls.sql

  echo "[4/4] Migration 010: Documents Metadata RLS"
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -f supabase/migrations/20250101000010_documents_metadata_rls.sql

# Option 2: Deploy all-in-one (default)
else
  echo "Deploying all-in-one migration file..."
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -f DEPLOY_STORAGE_ALL_IN_ONE.sql
fi

echo ""
echo "========================================="
echo "Verifying deployment..."
echo "========================================="

# Verify buckets
echo "Storage buckets:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "SELECT id, name, public, file_size_limit FROM storage.buckets WHERE id IN ('documents', 'raw-uploads');"

echo ""

# Verify functions
echo "Helper functions:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name LIKE '%yacht%' OR routine_name LIKE '%storage%' LIMIT 10;"

echo ""

# Verify RLS
echo "Storage RLS policies:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "SELECT COUNT(*) as policy_count FROM pg_policies WHERE schemaname = 'storage' AND tablename = 'objects';"

echo ""
echo "========================================="
echo "✅ Deployment complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Test upload: Use WORKER_5_QUICK_START.md"
echo "2. Verify isolation: Try cross-yacht access (should fail)"
echo "3. Check Supabase dashboard: Storage > Buckets"
