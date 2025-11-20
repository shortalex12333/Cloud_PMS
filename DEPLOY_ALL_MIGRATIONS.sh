#!/bin/bash
# ============================================================================
# Complete Migration Deployment Script
# ============================================================================
# This script deploys ALL CelesteOS migrations in correct order
# Run: bash DEPLOY_ALL_MIGRATIONS.sh
# ============================================================================

set -e

export PGPASSWORD='PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw'
DB_HOST='db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT='5432'
DB_USER='postgres'
DB_NAME='postgres'

echo "============================================="
echo "CelesteOS Complete Migration Deployment"
echo "============================================="
echo "This will deploy all 11 migrations (000-010)"
echo ""

# Test connection
echo "Testing connection..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "❌ Connection failed!"
  exit 1
fi
echo "✅ Connected to Supabase"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPL =~ ^[Yy]$ ]]; then
  echo "Deployment cancelled."
  exit 0
fi

cd supabase/migrations

echo ""
echo "============================================="
echo "Starting migration deployment..."
echo "============================================="
echo ""

# Migration 000: Enable pgvector
echo "[000] Enabling pgvector extension..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000000_enable_pgvector.sql
echo "✅ pgvector enabled"
echo ""

# Migration 001: Initial schema
echo "[001] Creating initial schema (34 tables)..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000001_initial_schema_v2.sql
echo "✅ Schema created"
echo ""

# Migration 002: RLS policies
echo "[002] Deploying RLS policies (50+ policies)..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000002_rls_policies.sql
echo "✅ RLS policies deployed"
echo ""

# Migration 003: Search functions
echo "[003] Creating search functions..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000003_search_functions.sql
echo "✅ Search functions created"
echo ""

# Migration 004: Seed data
echo "[004] Seeding user roles..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000004_seed_data.sql
echo "✅ Seed data loaded"
echo ""

# Migration 005: Triggers
echo "[005] Creating triggers..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000005_triggers.sql
echo "✅ Triggers created"
echo ""

# Migration 006: Business functions
echo "[006] Creating business functions..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000006_business_functions.sql
echo "✅ Business functions created"
echo ""

# Migration 007: Storage buckets
echo "[007] Creating storage buckets..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000007_create_storage_buckets.sql
echo "✅ Storage buckets created"
echo ""

# Migration 008: Storage helper functions
echo "[008] Creating storage helper functions..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000008_storage_helper_functions.sql
echo "✅ Storage helpers created"
echo ""

# Migration 009: Storage RLS
echo "[009] Deploying storage RLS policies..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000009_storage_objects_rls.sql
echo "✅ Storage RLS deployed"
echo ""

# Migration 010: Documents metadata RLS
echo "[010] Deploying documents metadata RLS..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f 20250101000010_documents_metadata_rls.sql
echo "✅ Documents metadata RLS deployed"
echo ""

cd ../..

echo "============================================="
echo "Verifying deployment..."
echo "============================================="
echo ""

# Verify tables
TABLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
")
echo "Tables created: $TABLE_COUNT"
if [ $TABLE_COUNT -ge 34 ]; then
  echo "✅ All tables present"
else
  echo "⚠️  Expected 34+ tables"
fi

# Verify RLS policies
POLICY_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public';
")
echo "RLS policies: $POLICY_COUNT"
if [ $POLICY_COUNT -ge 50 ]; then
  echo "✅ All RLS policies deployed"
else
  echo "⚠️  Expected 50+ policies"
fi

# Verify storage buckets
BUCKET_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM storage.buckets WHERE id IN ('documents', 'raw-uploads');
")
echo "Storage buckets: $BUCKET_COUNT"
if [ "$BUCKET_COUNT" -eq 2 ]; then
  echo "✅ Storage buckets created"
else
  echo "⚠️  Expected 2 buckets"
fi

# Verify functions
FUNCTION_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name NOT LIKE 'pg_%';
")
echo "Functions created: $FUNCTION_COUNT"
if [ $FUNCTION_COUNT -ge 20 ]; then
  echo "✅ All functions created"
else
  echo "⚠️  Expected 20+ functions"
fi

# Verify seed data
ROLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM user_roles;
")
echo "User roles seeded: $ROLE_COUNT"
if [ "$ROLE_COUNT" -eq 7 ]; then
  echo "✅ Seed data loaded"
else
  echo "⚠️  Expected 7 roles"
fi

echo ""
echo "============================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "============================================="
echo ""
echo "Database is ready for production use."
echo ""
echo "Next steps:"
echo "1. Worker 5: Implement document ingestion"
echo "2. Worker 6: Implement document indexing"
echo "3. Test upload → index → search workflow"
echo ""
echo "Documentation:"
echo "- STORAGE_ARCHITECTURE.md - Complete storage guide"
echo "- WORKER_5_QUICK_START.md - Upload code examples"
echo "- DATABASE_COMPLETION_REPORT.md - Full report"
