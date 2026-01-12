#!/bin/bash
# ============================================================================
# SUPABASE LOCAL START
# ============================================================================
# Starts local Supabase instance with migrations and seed data
# Usage: ./scripts/dev/supabase_start.sh
# ============================================================================

set -e  # Exit on error

echo "================================================"
echo "🚀 Starting Local Supabase"
echo "================================================"

# Navigate to repo root
cd "$(dirname "$0")/../.."

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found"
    echo "Install: brew install supabase/tap/supabase"
    exit 1
fi

echo ""
echo "📋 Configuration:"
echo "  - API Port: 54321"
echo "  - DB Port: 54322"
echo "  - Studio Port: 54323 (http://127.0.0.1:54323)"
echo "  - Inbucket (Email): 54324"
echo ""

# Start Supabase (this runs migrations automatically)
echo "▶️  Starting Supabase services..."
supabase start

# Check if start was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "✅ Supabase Started Successfully"
    echo "================================================"
    echo ""
    echo "📍 Endpoints:"
    echo "  - API URL: http://127.0.0.1:54321"
    echo "  - DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    echo "  - Studio: http://127.0.0.1:54323"
    echo "  - Inbucket (Email): http://127.0.0.1:54324"
    echo ""
    echo "🔑 Credentials (auto-generated):"
    supabase status | grep -E "(anon key|service_role key|JWT secret)"
    echo ""
    echo "💡 Next Steps:"
    echo "  1. Copy .env.local.example to .env.local (web and api)"
    echo "  2. Update NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321"
    echo "  3. Update anon key and service key from above"
    echo "  4. Run: ./scripts/dev/run_api.sh"
    echo "  5. Run: ./scripts/dev/run_web.sh (in separate terminal)"
    echo ""
    echo "🛠️  Management:"
    echo "  - Reset DB: ./scripts/dev/supabase_reset.sh"
    echo "  - Stop: ./scripts/dev/supabase_stop.sh"
    echo "  - Logs: supabase logs"
    echo "  - Status: supabase status"
    echo ""
else
    echo "❌ Failed to start Supabase"
    echo "Check logs: supabase logs"
    exit 1
fi
