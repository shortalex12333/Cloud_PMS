#!/bin/bash
#
# Apply match_link_targets_rpc migration to yTEST_YACHT_001
#
# This migration is required for L2.5 hybrid linking to function.
#

set -e

echo "================================================================"
echo "Applying match_link_targets_rpc Migration"
echo "================================================================"
echo ""

# Check for required env var
if [ -z "$yTEST_YACHT_001_SUPABASE_URL" ]; then
    echo "ERROR: yTEST_YACHT_001_SUPABASE_URL not set"
    echo "Please set environment variables from render_hadnover_env_vars.md"
    exit 1
fi

MIGRATION_FILE="supabase/migrations/20260206000003_match_link_targets_rpc.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo "ERROR: Migration file not found: $MIGRATION_FILE"
    exit 1
fi

echo "Migration file: $MIGRATION_FILE"
echo "Target: $yTEST_YACHT_001_SUPABASE_URL"
echo ""

# Extract project ref from URL
PROJECT_REF=$(echo "$yTEST_YACHT_001_SUPABASE_URL" | sed -n 's|https://\([^.]*\)\.supabase\.co|\1|p')

echo "Project ref: $PROJECT_REF"
echo ""

# Option 1: Manual SQL execution via Supabase Dashboard
echo "Option 1: Apply via Supabase Dashboard"
echo "----------------------------------------"
echo "1. Go to: https://supabase.com/dashboard/project/$PROJECT_REF/sql/new"
echo "2. Paste the contents of: $MIGRATION_FILE"
echo "3. Click 'Run'"
echo ""

# Option 2: Using psql (if database password is available)
echo "Option 2: Apply via psql"
echo "----------------------------------------"
echo "If you have the database password, run:"
echo ""
echo "  psql \"postgresql://postgres:[PASSWORD]@db.$PROJECT_REF.supabase.co:5432/postgres\" < $MIGRATION_FILE"
echo ""

# Option 3: Using Supabase CLI (requires project link)
echo "Option 3: Apply via Supabase CLI"
echo "----------------------------------------"
echo "1. Link project: supabase link --project-ref $PROJECT_REF"
echo "2. Push migration: supabase db push"
echo ""

# Check if migration is already applied
echo "Checking if migration is already applied..."
echo ""

# Use Supabase REST API to check for function
FUNCTION_CHECK=$(curl -s \
    -H "apikey: $yTEST_YACHT_001_SUPABASE_SERVICE_KEY" \
    -H "Authorization: Bearer $yTEST_YACHT_001_SUPABASE_SERVICE_KEY" \
    "$yTEST_YACHT_001_SUPABASE_URL/rest/v1/rpc/match_link_targets" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"p_yacht_id":"00000000-0000-0000-0000-000000000001","p_query":"test","p_limit":1}' \
    2>&1 || echo "not_found")

if echo "$FUNCTION_CHECK" | grep -q '"code":"PGRST202"'; then
    echo "✗ Migration NOT applied - function match_link_targets does not exist"
    echo ""
    echo "Please apply the migration using one of the options above."
    exit 1
elif echo "$FUNCTION_CHECK" | grep -q "not_found"; then
    echo "✗ Unable to check migration status (connection error)"
    echo ""
    echo "Please verify the migration is applied using one of the options above."
    exit 1
else
    echo "✓ Migration already applied - function match_link_targets exists"
    echo ""
fi

echo "================================================================"
echo "Migration check complete"
echo "================================================================"
