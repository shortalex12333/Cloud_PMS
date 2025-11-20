#!/bin/bash
# ============================================================================
# Deploy ALL Migrations to Supabase (Migrations 000-020)
# ============================================================================

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════"
echo "Deploying ALL Cloud PMS Migrations"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found!"
    echo ""
    echo "Install it first:"
    echo "  macOS:   brew install supabase/tap/supabase"
    echo "  Linux:   curl -fsSL https://raw.githubusercontent.com/supabase/cli/main/scripts/install.sh | sh"
    echo "  Windows: scoop install supabase"
    echo ""
    exit 1
fi

# Check if project is linked
if [ ! -f .supabase/config.toml ]; then
    echo "❌ Project not linked!"
    echo ""
    echo "Run these commands first:"
    echo "  supabase login"
    echo "  supabase link --project-ref vzsohavtuotocgrfkfyd"
    echo ""
    exit 1
fi

echo "✓ Supabase CLI found"
echo "✓ Project linked"
echo ""

# Show migration files
echo "Migrations to deploy:"
echo "─────────────────────────────────────────────────────────────"
ls -1 supabase/migrations/*.sql | while read file; do
    echo "  $(basename "$file")"
done
echo "─────────────────────────────────────────────────────────────"
echo ""

# Confirm
read -p "Deploy all migrations? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Deploying migrations..."
echo "─────────────────────────────────────────────────────────────"

# Deploy all migrations
supabase db push

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✓ DEPLOYMENT COMPLETE"
echo "════════════════════════════════════════════════════════════"
echo ""

# Verify deployment
echo "Verifying deployment..."
echo ""

# Check tables
echo "Tables created:"
supabase db query "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
" || echo "⚠ Could not verify tables"

echo ""

# Check storage buckets
echo "Storage buckets:"
supabase db query "
SELECT id, name, public, file_size_limit
FROM storage.buckets;
" || echo "⚠ Could not verify buckets"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✓ ALL DONE - Database is ready!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Create demo user in Supabase Dashboard → Authentication"
echo "2. Test Worker 4 upload with n8n"
echo "3. Verify hierarchical storage permissions"
echo ""
