#!/bin/bash
# =============================================================================
# CELESTE LOCAL DEVELOPMENT - Mac Studio (96GB RAM)
# =============================================================================
# Full observability local development environment
# Run your entire stack locally instead of paying cloud compute
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.local.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║  CELESTE LOCAL DEV - 96GB Mac Studio                              ║"
    echo "║  Full Observability • Zero Cloud Costs • Instant Feedback         ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

cmd_start() {
    print_header
    echo -e "${GREEN}Starting all services...${NC}"
    docker-compose -f "$COMPOSE_FILE" up --build -d
    echo ""
    echo -e "${GREEN}✓ Stack started!${NC}"
    echo ""
    cmd_status
}

cmd_stop() {
    echo -e "${YELLOW}Stopping all services...${NC}"
    docker-compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✓ Stack stopped${NC}"
}

cmd_reset() {
    echo -e "${RED}Stopping all services and removing volumes...${NC}"
    docker-compose -f "$COMPOSE_FILE" down -v
    echo -e "${GREEN}✓ Stack reset (all data cleared)${NC}"
}

cmd_logs() {
    local service="$1"
    if [ -n "$service" ]; then
        docker logs -f "celeste-$service"
    else
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

cmd_status() {
    echo -e "${BLUE}═══ SERVICE STATUS ═══${NC}"
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    echo -e "${BLUE}═══ RESOURCE USAGE ═══${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    echo ""
    echo -e "${BLUE}═══ ENDPOINTS ═══${NC}"
    echo "  API:      http://localhost:8000"
    echo "  Web:      http://localhost:3000"
    echo "  Postgres: localhost:5432"
    echo "  Redis:    localhost:6379"
    echo ""
}

cmd_stats() {
    echo -e "${BLUE}Live resource monitoring (Ctrl+C to exit)...${NC}"
    docker stats
}

cmd_shell() {
    local service="$1"
    if [ -z "$service" ]; then
        service="api"
    fi
    echo -e "${BLUE}Entering celeste-$service container...${NC}"
    docker container run --rm -it "celeste-$service" /bin/bash 2>/dev/null || \
    docker container run --rm -it "celeste-$service" /bin/sh
}

cmd_health() {
    echo -e "${BLUE}═══ HEALTH CHECKS ═══${NC}"

    echo -n "PostgreSQL: "
    if docker container ls --format '{{.Names}}' | grep -q celeste-postgres; then
        if docker inspect --format='{{.State.Health.Status}}' celeste-postgres 2>/dev/null | grep -q healthy; then
            echo -e "${GREEN}✓ Healthy${NC}"
        else
            echo -e "${YELLOW}○ Starting${NC}"
        fi
    else
        echo -e "${RED}✗ Not running${NC}"
    fi

    echo -n "Redis:      "
    if docker container ls --format '{{.Names}}' | grep -q celeste-redis; then
        if docker inspect --format='{{.State.Health.Status}}' celeste-redis 2>/dev/null | grep -q healthy; then
            echo -e "${GREEN}✓ Healthy${NC}"
        else
            echo -e "${YELLOW}○ Starting${NC}"
        fi
    else
        echo -e "${RED}✗ Not running${NC}"
    fi

    echo -n "API:        "
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi

    echo -n "Web:        "
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi
    echo ""
}

cmd_rebuild() {
    local service="$1"
    if [ -n "$service" ]; then
        echo -e "${YELLOW}Rebuilding $service...${NC}"
        docker-compose -f "$COMPOSE_FILE" up --build -d "$service"
    else
        echo -e "${YELLOW}Rebuilding all services...${NC}"
        docker-compose -f "$COMPOSE_FILE" up --build -d
    fi
    echo -e "${GREEN}✓ Rebuild complete${NC}"
}

cmd_nightly() {
    echo -e "${BLUE}Running nightly feedback loop manually...${NC}"
    docker-compose -f "$COMPOSE_FILE" run --rm nightly-feedback-loop
}

cmd_help() {
    print_header
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start              Start the full stack"
    echo "  stop               Stop all services"
    echo "  reset              Stop and remove all data (fresh start)"
    echo "  status             Show service status and resource usage"
    echo "  stats              Live resource monitoring"
    echo "  logs [service]     Follow logs (all services or specific one)"
    echo "  shell [service]    Open shell in container (default: api)"
    echo "  health             Check health of all services"
    echo "  rebuild [service]  Rebuild and restart (all or specific)"
    echo "  nightly            Run nightly feedback loop manually"
    echo ""
    echo "Services: api, web, postgres, redis, projection-worker,"
    echo "          cache-listener, embedding-worker"
    echo ""
    echo "Examples:"
    echo "  $0 start           # Start everything"
    echo "  $0 logs api        # Follow API logs"
    echo "  $0 shell api       # Shell into API container"
    echo "  $0 rebuild api     # Rebuild just the API"
    echo ""
}

# Main command router
case "${1:-help}" in
    start)    cmd_start ;;
    stop)     cmd_stop ;;
    reset)    cmd_reset ;;
    logs)     cmd_logs "$2" ;;
    status)   cmd_status ;;
    stats)    cmd_stats ;;
    shell)    cmd_shell "$2" ;;
    health)   cmd_health ;;
    rebuild)  cmd_rebuild "$2" ;;
    nightly)  cmd_nightly ;;
    help|*)   cmd_help ;;
esac
