#!/bin/bash
#
# ML Seeding Execution Script
# Runs REST API-based adversarial keyword seeder with correct credentials
#

set -e

cd "$(dirname "$0")/.."

echo "🚀 Executing ML Seeding via REST API..."
echo ""

# Export environment variables
export TENANT_1_SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
export TENANT_1_SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

# Install dependencies if needed
if ! python3 -c "import requests" 2>/dev/null; then
    echo "📦 Installing required Python packages..."
    pip3 install requests
fi

# Run the seeder
python3 scripts/seed_adversarial_rest.py "$@"

echo ""
echo "✅ ML Seeding Complete!"
echo ""
echo "Next steps:"
echo "  1. Run Shard 11 tests: cd apps/web && npx playwright test e2e/shard-11-extremecases"
echo "  2. Verify pass rate improved from 39.6% to 85%+"
