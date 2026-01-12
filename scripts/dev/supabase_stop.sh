#!/bin/bash
# ============================================================================
# SUPABASE LOCAL STOP
# ============================================================================
# Stops local Supabase instance (preserves data)
# Usage: ./scripts/dev/supabase_stop.sh
# ============================================================================

set -e  # Exit on error

echo "================================================"
echo "🛑 Stopping Local Supabase"
echo "================================================"

# Navigate to repo root
cd "$(dirname "$0")/../.."

# Check if Supabase is running
if ! supabase status &> /dev/null; then
    echo "ℹ️  Supabase is not running"
    exit 0
fi

echo ""
echo "▶️  Stopping Supabase services..."
supabase stop

# Check if stop was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "✅ Supabase Stopped Successfully"
    echo "================================================"
    echo ""
    echo "💡 Data is preserved - restart with:"
    echo "   ./scripts/dev/supabase_start.sh"
    echo ""
else
    echo "❌ Failed to stop Supabase"
    exit 1
fi
