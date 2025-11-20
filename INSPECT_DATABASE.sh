#!/bin/bash
# ============================================================================
# Database Inspection Script
# ============================================================================
# This script checks the current state of the Supabase database
# Run: bash INSPECT_DATABASE.sh > database_status.txt
# ============================================================================

set -e

export PGPASSWORD='PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw'
DB_HOST='db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT='5432'
DB_USER='postgres'
DB_NAME='postgres'

echo "============================================="
echo "CelesteOS Database Inspection Report"
echo "============================================="
echo "Date: $(date)"
echo ""

# Test connection
echo "[1/10] Testing database connection..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "❌ Connection failed!"
  exit 1
fi
echo "✅ Connected to Supabase"
echo ""

# Check pgvector extension
echo "[2/10] Checking pgvector extension..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT
  CASE
    WHEN COUNT(*) = 1 THEN '✅ pgvector ENABLED (version: ' || extversion || ')'
    ELSE '❌ pgvector NOT ENABLED'
  END
FROM pg_extension
WHERE extname = 'vector';
"
echo ""

# Check tables count
echo "[3/10] Checking tables in public schema..."
TABLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*)
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
")
echo "Total tables: $TABLE_COUNT"

if [ $TABLE_COUNT -ge 34 ]; then
  echo "✅ Expected table count (34+) met"
else
  echo "⚠️  Expected 34 tables, found $TABLE_COUNT"
fi

echo ""
echo "Table list:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
"
echo ""

# Check critical tables
echo "[4/10] Checking critical tables..."
CRITICAL_TABLES="yachts users agents api_keys documents document_chunks equipment work_orders"
for table in $CRITICAL_TABLES; do
  EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = '$table';
  ")
  if [ "$EXISTS" -eq 1 ]; then
    echo "✅ $table"
  else
    echo "❌ $table MISSING"
  fi
done
echo ""

# Check vector dimension
echo "[5/10] Checking vector dimension (CRITICAL)..."
VECTOR_DIM=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT
  CASE
    WHEN data_type LIKE '%1536%' OR udt_name LIKE '%1536%' THEN '✅ vector(1536) - CORRECT (OpenAI compatible)'
    WHEN column_name IS NOT NULL THEN '❌ WRONG dimension (should be 1536)'
    ELSE '❌ embedding column NOT FOUND'
  END
FROM information_schema.columns
WHERE table_name = 'document_chunks' AND column_name = 'embedding';
" 2>/dev/null || echo "⚠️  document_chunks table not found")
echo "$VECTOR_DIM"
echo ""

# Check RLS enabled
echo "[6/10] Checking RLS enabled on tables..."
RLS_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(DISTINCT c.relname)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND c.relrowsecurity = true;
")
echo "Tables with RLS enabled: $RLS_COUNT"
if [ $RLS_COUNT -ge 34 ]; then
  echo "✅ RLS enabled on all tables"
else
  echo "⚠️  Expected RLS on 34 tables, found $RLS_COUNT"
fi
echo ""

# Check RLS policies count
echo "[7/10] Checking RLS policies..."
POLICY_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*)
FROM pg_policies
WHERE schemaname = 'public';
")
echo "Total RLS policies: $POLICY_COUNT"
if [ $POLICY_COUNT -ge 50 ]; then
  echo "✅ Expected policy count (50+) met"
else
  echo "⚠️  Expected 50+ policies, found $POLICY_COUNT"
fi
echo ""

# Check storage buckets
echo "[8/10] Checking Supabase Storage buckets..."
BUCKET_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*)
FROM storage.buckets
WHERE id IN ('documents', 'raw-uploads');
" 2>/dev/null || echo "0")
echo "Storage buckets found: $BUCKET_COUNT"
if [ "$BUCKET_COUNT" -eq 2 ]; then
  echo "✅ Both storage buckets exist (documents, raw-uploads)"
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
  SELECT id, name, public, file_size_limit
  FROM storage.buckets
  WHERE id IN ('documents', 'raw-uploads');
  "
elif [ "$BUCKET_COUNT" -eq 0 ]; then
  echo "❌ Storage buckets NOT created (need migration 007)"
else
  echo "⚠️  Partial: found $BUCKET_COUNT buckets, expected 2"
fi
echo ""

# Check helper functions
echo "[9/10] Checking helper functions..."
FUNCTION_LIST="get_yacht_id get_user_yacht_id extract_yacht_id_from_path can_access_document validate_storage_path_format match_documents"
FOUND_FUNCS=0
for func in $FUNCTION_LIST; do
  EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
    SELECT COUNT(*)
    FROM information_schema.routines
    WHERE routine_schema = 'public' AND routine_name = '$func';
  ")
  if [ "$EXISTS" -eq 1 ]; then
    echo "✅ $func"
    FOUND_FUNCS=$((FOUND_FUNCS + 1))
  fi
done
echo "Total helper functions found: $FOUND_FUNCS"
echo ""

# Check user_roles seed data
echo "[10/10] Checking seed data..."
ROLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM user_roles;
" 2>/dev/null || echo "0")
echo "User roles seeded: $ROLE_COUNT"
if [ "$ROLE_COUNT" -eq 7 ]; then
  echo "✅ All 7 roles seeded"
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
  SELECT role_name, display_name FROM user_roles ORDER BY role_name;
  "
elif [ "$ROLE_COUNT" -eq 0 ]; then
  echo "❌ No roles seeded (need migration 004)"
else
  echo "⚠️  Partial: found $ROLE_COUNT roles, expected 7"
fi
echo ""

# Summary
echo "============================================="
echo "SUMMARY & RECOMMENDATIONS"
echo "============================================="
echo ""

# Determine what needs to be deployed
NEEDS_DEPLOYMENT=()

if [ $TABLE_COUNT -lt 34 ]; then
  NEEDS_DEPLOYMENT+=("Migration 001: Initial Schema (34 tables)")
fi

if ! echo "$VECTOR_DIM" | grep -q "1536"; then
  NEEDS_DEPLOYMENT+=("Migration 001: Fix vector dimension to 1536")
fi

if [ $POLICY_COUNT -lt 50 ]; then
  NEEDS_DEPLOYMENT+=("Migration 002: RLS Policies")
fi

if [ $FOUND_FUNCS -lt 6 ]; then
  NEEDS_DEPLOYMENT+=("Migration 003: Search Functions")
  NEEDS_DEPLOYMENT+=("Migration 006: Business Functions")
  NEEDS_DEPLOYMENT+=("Migration 008: Storage Helper Functions")
fi

if [ "$ROLE_COUNT" -lt 7 ]; then
  NEEDS_DEPLOYMENT+=("Migration 004: Seed Data (user roles)")
fi

if [ "$BUCKET_COUNT" -lt 2 ]; then
  NEEDS_DEPLOYMENT+=("Migration 007: Storage Buckets")
  NEEDS_DEPLOYMENT+=("Migration 009: Storage RLS")
  NEEDS_DEPLOYMENT+=("Migration 010: Documents Metadata RLS")
fi

if [ ${#NEEDS_DEPLOYMENT[@]} -eq 0 ]; then
  echo "✅ DATABASE IS COMPLETE!"
  echo ""
  echo "All migrations have been deployed successfully."
  echo "Ready for production use."
else
  echo "⚠️  MISSING MIGRATIONS:"
  echo ""
  for item in "${NEEDS_DEPLOYMENT[@]}"; do
    echo "  - $item"
  done
  echo ""
  echo "Run deployment script:"
  echo "  bash DEPLOY_ALL_MIGRATIONS.sh"
fi

echo ""
echo "============================================="
echo "Inspection complete!"
echo "============================================="
