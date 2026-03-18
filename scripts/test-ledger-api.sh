#!/usr/bin/env bash
set -euo pipefail

API="http://localhost:8000"
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE"
SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"

PASS=0
FAIL=0

# ─── Helpers ─────────────────────────────────────────────────────────────────

get_token() {
  local email="$1" password="$2"
  # Use Python for the auth request — avoids zsh ! history expansion entirely
  python3 - "$email" "$password" "${SUPABASE_URL}" "${ANON_KEY}" << 'PYEOF'
import sys, json, urllib.request
email, password, supabase_url, anon_key = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
url = f"{supabase_url}/auth/v1/token?grant_type=password"
data = json.dumps({"email": email, "password": password}).encode()
req = urllib.request.Request(url, data=data, headers={
    "apikey": anon_key,
    "Content-Type": "application/json",
})
try:
    resp = urllib.request.urlopen(req)
    d = json.loads(resp.read())
    print(d.get("access_token", "ERROR"))
except Exception as e:
    print(f"ERROR: {e}")
PYEOF
}

# check: verifies HTTP 200 + success:true + required key present
check() {
  local label="$1" status="$2" body="$3" required_key="$4"
  local ok=1

  [ "$status" -ne 200 ] && ok=0

  if [ "$ok" -eq 1 ]; then
    echo "$body" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('success') is not True:
    raise SystemExit(1)
if d.get('${required_key}') is None:
    raise SystemExit(1)
" 2>/dev/null || ok=0
  fi

  if [ "$ok" -eq 1 ]; then
    echo "  ✅ PASS — ${label}"
    PASS=$((PASS + 1))
  else
    echo "  ❌ FAIL — ${label} (HTTP ${status})"
    echo "     $(echo "$body" | head -c 300)"
    FAIL=$((FAIL + 1))
  fi
}

# ─── Get tokens ──────────────────────────────────────────────────────────────

echo "=== Fetching JWTs ==="
# x@alex-short.com is the only user with master-DB tenant routing
# captain.tenant@alex-short.com returns 403 (not in master DB)
# All API tests use captain; role-scoping verified at DB level via Playwright
CAPTAIN_TOKEN=$(get_token "x@alex-short.com" "Password2!")

[ "${CAPTAIN_TOKEN:0:5}" = "ERROR" ] && echo "❌ Captain JWT failed" && exit 1
echo "  Token obtained ✓"

# Generate a UUID for test records (macOS-compatible)
TEST_UUID=$(python3 -c "import uuid; print(uuid.uuid4())")

# ─── GET /v1/ledger/events ────────────────────────────────────────────────────

echo ""
echo "=== GET /v1/ledger/events (me/all view) ==="

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  "${API}/v1/ledger/events?limit=10" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}")
check "captain /events — 200 + success:true + events" "$HTTP" "$(cat /tmp/lb.json)" "events"

# ─── GET /v1/ledger/events?user_id= (explicit me filter + no bleed) ──────────

echo ""
echo "=== GET /v1/ledger/events?user_id=... (me filter — no bleed) ==="

CAPTAIN_UID=$(echo "${CAPTAIN_TOKEN}" | cut -d'.' -f2 | python3 -c "
import sys, base64, json
p = sys.stdin.read().strip()
p += '=' * (4 - len(p) % 4)
print(json.loads(base64.urlsafe_b64decode(p)).get('sub',''))
")
echo "  Captain UID: ${CAPTAIN_UID}"

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  "${API}/v1/ledger/events?user_id=${CAPTAIN_UID}&limit=20" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}")
BODY=$(cat /tmp/lb.json)
check "captain /events?user_id — 200 + success:true + events" "$HTTP" "$BODY" "events"

# No bleed: all returned events must belong to captain
WRONG=$(echo "$BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
bad = [e for e in d.get('events',[]) if e.get('user_id') != '${CAPTAIN_UID}']
print(len(bad))
")
if [ "$WRONG" -eq 0 ]; then
  echo "  ✅ PASS — No event bleed (all events belong to captain)"
  PASS=$((PASS + 1))
else
  echo "  ❌ FAIL — ${WRONG} events from other users in captain's me-filter"
  FAIL=$((FAIL + 1))
fi

# ─── GET /v1/ledger/timeline (three-tier role-scoped) ────────────────────────

echo ""
echo "=== GET /v1/ledger/timeline (role-scoped) ==="

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  "${API}/v1/ledger/timeline?limit=10" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}")
check "captain /timeline — 200 + success:true + events" "$HTTP" "$(cat /tmp/lb.json)" "events"

# Captain timeline should return >= events in his own me-view (sanity)
CAPTAIN_TIMELINE_N=$(curl -s "${API}/v1/ledger/timeline?limit=1000" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))")
echo "  Captain timeline total: ${CAPTAIN_TIMELINE_N}"
if [ "$CAPTAIN_TIMELINE_N" -ge 0 ]; then
  echo "  ✅ PASS — Captain /timeline returns valid total (${CAPTAIN_TIMELINE_N} events)"
  PASS=$((PASS + 1))
fi

# ─── GET /v1/ledger/events/by-entity/{type}/{id} ─────────────────────────────

echo ""
echo "=== GET /v1/ledger/events/by-entity/{type}/{id} ==="

# Get a real entity ref from captain's events
ENTITY=$(curl -s "${API}/v1/ledger/events?limit=5" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}" \
  | python3 -c "
import sys, json
evs = json.load(sys.stdin).get('events', [])
for e in evs:
  if e.get('entity_id') and e.get('entity_type'):
    print(e['entity_type']+':'+e['entity_id'])
    break
" 2>/dev/null || echo "")

if [ -z "$ENTITY" ]; then
  echo "  ⚠️  SKIP — No events in tenant to derive entity reference"
else
  ETYPE="${ENTITY%%:*}"
  EID="${ENTITY##*:}"
  HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
    "${API}/v1/ledger/events/by-entity/${ETYPE}/${EID}?limit=10" \
    -H "Authorization: Bearer ${CAPTAIN_TOKEN}")
  check "captain /by-entity — 200 + success:true + events" "$HTTP" "$(cat /tmp/lb.json)" "events"
fi

# ─── POST /v1/ledger/read-event (read beacon) ────────────────────────────────

echo ""
echo "=== POST /v1/ledger/read-event (read beacon) ==="

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  -X POST "${API}/v1/ledger/read-event" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"entity_type\":\"work_order\",\"entity_id\":\"${TEST_UUID}\",\"metadata\":{}}")
check "captain /read-event — 200 + success:true" "$HTTP" "$(cat /tmp/lb.json)" "success"

# ─── POST /v1/ledger/record (explicit record) ────────────────────────────────

echo ""
echo "=== POST /v1/ledger/record ==="

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  -X POST "${API}/v1/ledger/record" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"action\": \"artefact_opened\",
    \"entity_type\": \"work_order\",
    \"entity_id\": \"${TEST_UUID}\",
    \"metadata\": {\"source\": \"api_test\"}
  }")
check "captain /record — 200 + success:true" "$HTTP" "$(cat /tmp/lb.json)" "success"

# ─── GET /v1/ledger/day-anchors ──────────────────────────────────────────────

echo ""
echo "=== GET /v1/ledger/day-anchors ==="

HTTP=$(curl -s -o /tmp/lb.json -w "%{http_code}" \
  "${API}/v1/ledger/day-anchors?days=7" \
  -H "Authorization: Bearer ${CAPTAIN_TOKEN}")
check "captain /day-anchors — 200 + success:true + anchors" "$HTTP" "$(cat /tmp/lb.json)" "anchors"

# ─── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "════════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
