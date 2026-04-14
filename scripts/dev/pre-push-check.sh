#!/bin/bash
# pre-push-check.sh — Run before git push. Docker must pass before Render sees code.
# Usage: bash scripts/dev/pre-push-check.sh
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "=== [1/4] Build API Docker image ==="
docker compose --profile api build

echo "=== [2/4] Start container ==="
docker compose --profile api up -d
# Wait for startup
for i in $(seq 1 15); do
  if curl -fsS http://localhost:8000/health > /dev/null 2>&1; then
    break
  fi
  [ $i -eq 15 ] && echo "Container failed to start in time" && docker compose --profile api down && exit 1
  sleep 1
done

echo "=== [3/4] Healthcheck ==="
curl -fsS http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('status')=='healthy' else 1)"

echo "=== [4/4] Certificate handler tests ==="
SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co" \
SUPABASE_SERVICE_KEY="${TENANT_1_SUPABASE_SERVICE_KEY}" \
MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co" \
MASTER_SUPABASE_JWT_SECRET="${MASTER_SUPABASE_JWT_SECRET}" \
FEATURE_CERTIFICATES="true" \
python3 apps/api/tests/cert_binary_tests.py

echo "=== Tear down ==="
docker compose --profile api down

echo ""
echo "ALL CHECKS PASSED — safe to push."
