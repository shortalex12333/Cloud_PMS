#!/bin/bash
# =============================================================================
# Celeste Worker Watchdog
# =============================================================================
# Runs every 5 minutes via macOS LaunchAgent.
# Checks Docker health status for all 4 Celeste workers.
# Sends a macOS notification and logs any unhealthy container.
# Auto-restarts containers that are confirmed unhealthy.
#
# Install (one-time):
#   cp ~/Library/LaunchAgents/com.celeste.worker-watchdog.plist (see below)
#   launchctl load ~/Library/LaunchAgents/com.celeste.worker-watchdog.plist
#
# Logs: /tmp/celeste_watchdog.log
# =============================================================================

PROJECT_DIR="/Users/celeste7/Documents/Cloud_PMS"
LOG_FILE="/tmp/celeste_watchdog.log"
WORKERS=("cache-listener" "projection-worker" "embedding-worker" "email-watcher")
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

notify() {
    local title="$1"
    local message="$2"
    osascript -e "display notification \"$message\" with title \"$title\" sound name \"Basso\"" 2>/dev/null || true
}

# Check the volume is mounted
if [ ! -d "$PROJECT_DIR" ]; then
    log "ERROR: Project directory not mounted at $PROJECT_DIR"
    notify "Celeste Watchdog" "Backup volume not mounted — workers cannot be checked"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

# Use full paths — LaunchAgent has a minimal PATH that won't find /usr/local/bin
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Check Docker is running
if ! docker info &>/dev/null; then
    log "ERROR: Docker is not running"
    notify "Celeste Watchdog" "Docker is not running — all workers offline"
    exit 1
fi

unhealthy_count=0
not_running_count=0
issues=()

for worker in "${WORKERS[@]}"; do
    container="cloud_pms-${worker}-1"

    # Get container status
    status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)
    health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)

    if [ -z "$status" ]; then
        log "MISSING: $worker — container does not exist"
        issues+=("$worker: not found")
        ((not_running_count++))
        continue
    fi

    if [ "$status" != "running" ]; then
        log "DOWN: $worker — status=$status"
        issues+=("$worker: $status")
        ((not_running_count++))

        # Attempt restart
        log "Attempting restart of $worker..."
        docker-compose --profile workers up -d "$worker" >> "$LOG_FILE" 2>&1
        if [ $? -eq 0 ]; then
            log "Restarted $worker successfully"
        else
            log "Failed to restart $worker"
        fi
        continue
    fi

    if [ "$health" = "unhealthy" ]; then
        # Get the last health check output for context
        last_output=$(docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' "$container" 2>/dev/null | tail -c 200)
        log "UNHEALTHY: $worker — $last_output"
        issues+=("$worker: unhealthy")
        ((unhealthy_count++))

        # Restart unhealthy container
        log "Restarting unhealthy $worker..."
        docker-compose restart "$worker" >> "$LOG_FILE" 2>&1
        if [ $? -eq 0 ]; then
            log "Restarted $worker after unhealthy status"
        else
            log "Failed to restart $worker"
        fi
        continue
    fi

    log "OK: $worker — status=$status health=${health:-no_check}"
done

# Send a single notification summarising all issues
total_issues=$((unhealthy_count + not_running_count))
if [ $total_issues -gt 0 ]; then
    issue_summary=$(IFS=', '; echo "${issues[*]}")
    notify "Celeste Worker Alert" "$total_issues worker(s) had issues: $issue_summary"
    log "ALERT sent: $issue_summary"
else
    log "All workers healthy"
fi

exit 0
