#!/bin/bash
# ============================================================================
# SUPABASE LOCAL RESET
# ============================================================================
# Resets local database to clean state (re-runs migrations + seed data)
# Usage: ./scripts/dev/supabase_reset.sh
# ============================================================================

set -e  # Exit on error

echo "================================================"
echo "🔄 Resetting Local Supabase Database"
echo "================================================"

# Navigate to repo root
cd "$(dirname "$0")/../.."

# Check if Supabase is running
if ! supabase status &> /dev/null; then
    echo "⚠️  Supabase is not running"
    echo "Start with: ./scripts/dev/supabase_start.sh"
    exit 1
fi

echo ""
echo "⚠️  WARNING: This will DELETE all local data"
echo "This includes:"
echo "  - All database tables"
echo "  - All storage objects"
echo "  - All auth users"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Reset cancelled"
    exit 0
fi

echo ""
echo "▶️  Resetting database..."
supabase db reset

# Check if reset was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "✅ Database Reset Successfully"
    echo "================================================"
    echo ""
    echo "📊 Seed Data Loaded:"
    echo "  - 1 yacht (M/Y Test Vessel)"
    echo "  - 2 users (admin@test.com, crew@test.com)"
    echo "  - 1 equipment (Main Generator #1)"
    echo "  - 1 part (Oil Filter)"
    echo "  - 1 document (Generator Manual)"
    echo "  - 1 work order (500hr Maintenance)"
    echo "  - 1 shopping list item (Oil Filter reorder)"
    echo ""
    echo "🔑 Test Credentials:"
    echo "  - Admin: admin@test.com / password123"
    echo "  - Crew: crew@test.com / password123"
    echo ""
    echo "💡 Note: You need to create auth users separately via:"
    echo "  - Supabase Studio (http://127.0.0.1:54323)"
    echo "  - Or API signup endpoint"
    echo ""
else
    echo "❌ Failed to reset database"
    echo "Check logs: supabase logs"
    exit 1
fi
