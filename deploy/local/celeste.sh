#!/bin/bash
# =============================================================================
# CelesteOS Local Stack — CLI
# =============================================================================
# Full replacement for Render. All services run locally.
# Saves $75/month in Render compute.
#
# Usage:
#   ./celeste.sh start        # API + background workers
#   ./celeste.sh start-all    # API + workers + web frontend
#   ./celeste.sh stop          # Stop everything
#   ./celeste.sh logs [svc]    # Follow logs (api, projection, embedding, web)
#   ./celeste.sh status        # Service status + resource usage
#   ./celeste.sh search "q"    # Quick search test (mints JWT, hits SSE)
#   ./celeste.sh health        # Health check all services
#   ./celeste.sh rebuild [svc] # Rebuild and restart
#   ./celeste.sh nightly       # Run nightly feedback loop manually
#   ./celeste.sh shell [svc]   # Shell into container
#   ./celeste.sh db-check      # Verify DB connection
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE="docker compose -f $SCRIPT_DIR/docker-compose.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

header() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  CelesteOS Local Stack                                    ║"
    echo "║  Render replacement · \$0/month · Full observability       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

cmd_start() {
    header
    echo -e "${GREEN}Starting API + background workers...${NC}"
    $COMPOSE up --build -d api projection embedding
    echo ""
    cmd_status
}

cmd_start_all() {
    header
    echo -e "${GREEN}Starting full stack (API + workers + frontend)...${NC}"
    $COMPOSE --profile frontend up --build -d
    echo ""
    cmd_status
}

cmd_stop() {
    echo -e "${YELLOW}Stopping all services...${NC}"
    $COMPOSE --profile frontend --profile cron down
    echo -e "${GREEN}Done.${NC}"
}

cmd_logs() {
    local svc="${1:-}"
    if [ -n "$svc" ]; then
        docker logs -f "celeste-$svc" 2>/dev/null || \
        $COMPOSE logs -f "$svc"
    else
        $COMPOSE logs -f
    fi
}

cmd_status() {
    echo -e "${BLUE}═══ SERVICES ═══${NC}"
    $COMPOSE ps 2>/dev/null
    echo ""
    echo -e "${BLUE}═══ RESOURCES ═══${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null | grep celeste || true
    echo ""
    echo -e "${BLUE}═══ ENDPOINTS ═══${NC}"
    echo "  API:  http://localhost:8000"
    echo "  Web:  http://localhost:3000  (if started with start-all)"
    echo ""
}

cmd_health() {
    echo -e "${BLUE}═══ HEALTH ═══${NC}"

    echo -n "  API:        "
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Down${NC}"
    fi

    echo -n "  F1 Search:  "
    if curl -sf http://localhost:8000/api/f1/search/health > /dev/null 2>&1; then
        local info=$(curl -s http://localhost:8000/api/f1/search/health)
        local caps=$(echo "$info" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('capabilities',[])))" 2>/dev/null || echo "?")
        echo -e "${GREEN}✓ Healthy${NC} (${caps} capabilities)"
    else
        echo -e "${RED}✗ Down${NC}"
    fi

    echo -n "  Projection: "
    if docker ps --format '{{.Names}}' | grep -q celeste-projection; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${DIM}○ Not started${NC}"
    fi

    echo -n "  Embedding:  "
    if docker ps --format '{{.Names}}' | grep -q celeste-embedding; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${DIM}○ Not started${NC}"
    fi

    echo -n "  Web:        "
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${DIM}○ Not started${NC}"
    fi

    echo ""
}

cmd_rebuild() {
    local svc="${1:-}"
    if [ -n "$svc" ]; then
        echo -e "${YELLOW}Rebuilding $svc...${NC}"
        $COMPOSE up --build -d "$svc"
    else
        echo -e "${YELLOW}Rebuilding all...${NC}"
        $COMPOSE up --build -d api projection embedding
    fi
    echo -e "${GREEN}Done.${NC}"
}

cmd_nightly() {
    echo -e "${BLUE}Running nightly feedback loop...${NC}"
    $COMPOSE --profile cron run --rm nightly
}

cmd_shell() {
    local svc="${1:-api}"
    echo -e "${BLUE}Shell into celeste-$svc...${NC}"
    docker exec -it "celeste-$svc" /bin/bash 2>/dev/null || \
    docker exec -it "celeste-$svc" /bin/sh
}

cmd_db_check() {
    echo -e "${BLUE}═══ DATABASE CHECK ═══${NC}"
    echo -n "  Tenant DB (direct :5432): "
    if docker exec celeste-api python3 -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    count = await conn.fetchval('SELECT count(*) FROM search_index')
    await conn.close()
    return count
print(asyncio.run(check()))
" 2>/dev/null; then
        echo -e "  ${GREEN}✓ Connected${NC} (search_index rows above)"
    else
        echo -e "  ${RED}✗ Failed${NC}"
    fi

    echo -n "  Embedding coverage: "
    docker exec celeste-api python3 -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    total = await conn.fetchval('SELECT count(*) FROM search_index')
    with_vec = await conn.fetchval('SELECT count(*) FROM search_index WHERE embedding_1536 IS NOT NULL')
    await conn.close()
    pct = (with_vec/total*100) if total > 0 else 0
    print(f'{with_vec}/{total} ({pct:.1f}%)')
asyncio.run(check())
" 2>/dev/null || echo "  (API not running)"
    echo ""
}

cmd_search() {
    local query="$1"
    if [ -z "$query" ]; then
        echo "Usage: $0 search \"your query\""
        exit 1
    fi

    echo -e "${BLUE}Searching: \"$query\"${NC}"
    python3 << PYEOF
import urllib.request, json, time, jwt

# Get first user from Master Supabase
skey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q'
url = 'https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/admin/users?page=1&per_page=1'
req = urllib.request.Request(url)
req.add_header('apikey', skey)
req.add_header('Authorization', f'Bearer {skey}')
resp = urllib.request.urlopen(req)
users = json.loads(resp.read()).get('users', [])
uid, email = users[0]['id'], users[0]['email']

# Mint JWT
secret = 'wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw=='
token = jwt.encode({
    'sub': uid, 'aud': 'authenticated', 'role': 'authenticated',
    'iss': 'supabase', 'iat': int(time.time()), 'exp': int(time.time()) + 3600,
    'email': email
}, secret, algorithm='HS256')

# SSE search
q = urllib.parse.quote("$query")
req2 = urllib.request.Request(f'http://localhost:8000/api/f1/search/stream?q={q}')
req2.add_header('Authorization', f'Bearer {token}')
req2.add_header('Accept', 'text/event-stream')

start = time.time()
try:
    resp2 = urllib.request.urlopen(req2, timeout=30)
    data = resp2.read().decode()
    elapsed = (time.time() - start) * 1000

    for chunk in data.split('\n\n'):
        lines = chunk.strip().split('\n')
        ename, edata = None, None
        for l in lines:
            if l.startswith('event: '): ename = l[7:]
            if l.startswith('data: '): edata = l[6:]
        if not ename or not edata: continue
        d = json.loads(edata)
        if ename == 'result_batch':
            for item in d['items'][:10]:
                p = item['payload']
                name = p.get('name') or p.get('label') or p.get('subject', '?')
                print(f"  {item['object_type']:14s} {name[:50]}")
        elif ename == 'finalized':
            print(f"\n  {d['total_results']} results in {d['latency_ms']:.0f}ms (stream: {elapsed:.0f}ms)")
            print(f"  text={d['hybrid_search']['text_results']} vector={d['hybrid_search']['vector_results']}")
except urllib.error.HTTPError as e:
    print(f'  ERROR: HTTP {e.code}: {e.read().decode()[:200]}')
except Exception as e:
    print(f'  ERROR: {e}')
PYEOF
}

cmd_help() {
    header
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Lifecycle:"
    echo "  start              API + background workers (projection, embedding)"
    echo "  start-all          API + workers + web frontend"
    echo "  stop               Stop everything"
    echo "  rebuild [svc]      Rebuild and restart (api, projection, embedding, web)"
    echo ""
    echo "Observability:"
    echo "  logs [svc]         Follow logs (default: all)"
    echo "  status             Service status + resource usage"
    echo "  health             Health check all endpoints"
    echo "  db-check           Verify DB connection + embedding coverage"
    echo ""
    echo "Testing:"
    echo "  search \"query\"     Quick F1 search test (mints JWT, hits SSE)"
    echo "  shell [svc]        Shell into container (default: api)"
    echo "  nightly            Run nightly feedback loop manually"
    echo ""
    echo "Services: api, projection, embedding, web, nightly"
    echo ""
}

# Route
case "${1:-help}" in
    start)      cmd_start ;;
    start-all)  cmd_start_all ;;
    stop)       cmd_stop ;;
    logs)       cmd_logs "$2" ;;
    status)     cmd_status ;;
    health)     cmd_health ;;
    rebuild)    cmd_rebuild "$2" ;;
    nightly)    cmd_nightly ;;
    shell)      cmd_shell "$2" ;;
    db-check)   cmd_db_check ;;
    search)     cmd_search "$2" ;;
    help|*)     cmd_help ;;
esac
