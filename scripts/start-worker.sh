#!/bin/bash
# Start a Claude Code worker with the appropriate configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 <frontend|backend> [--worktree]"
    echo ""
    echo "Options:"
    echo "  frontend    Start frontend worker (apps/web)"
    echo "  backend     Start backend worker (apps/api, supabase)"
    echo "  --worktree  Create isolated git worktree (recommended for parallel work)"
    echo ""
    echo "Examples:"
    echo "  $0 frontend              # Start frontend worker in main repo"
    echo "  $0 backend --worktree    # Start backend worker in isolated worktree"
    exit 1
}

if [ $# -lt 1 ]; then
    usage
fi

WORKER_TYPE=$1
USE_WORKTREE=false

if [ "$2" == "--worktree" ]; then
    USE_WORKTREE=true
fi

case $WORKER_TYPE in
    frontend)
        CONFIG_FILE="$PROJECT_ROOT/docs/AGENTS/FRONTEND_WORKER.md"
        WORKTREE_NAME="cloud_pms_frontend"
        BRANCH_NAME="feature/frontend-$(date +%Y%m%d)"
        ;;
    backend)
        CONFIG_FILE="$PROJECT_ROOT/docs/AGENTS/BACKEND_WORKER.md"
        WORKTREE_NAME="cloud_pms_backend"
        BRANCH_NAME="feature/backend-$(date +%Y%m%d)"
        ;;
    *)
        echo "Error: Unknown worker type '$WORKER_TYPE'"
        usage
        ;;
esac

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

if [ "$USE_WORKTREE" = true ]; then
    WORKTREE_PATH="$PROJECT_ROOT/../$WORKTREE_NAME"

    if [ -d "$WORKTREE_PATH" ]; then
        echo "Worktree already exists at $WORKTREE_PATH"
        echo "Using existing worktree..."
    else
        echo "Creating worktree at $WORKTREE_PATH..."
        cd "$PROJECT_ROOT"
        git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" 2>/dev/null || \
        git worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
    fi

    # Copy config to worktree
    cp "$CONFIG_FILE" "$WORKTREE_PATH/CLAUDE.md"
    echo "Copied $WORKER_TYPE config to $WORKTREE_PATH/CLAUDE.md"

    cd "$WORKTREE_PATH"
    echo ""
    echo "Starting Claude Code in $WORKTREE_PATH..."
    echo "Worker type: $WORKER_TYPE"
    echo ""
else
    # Use main repo
    cp "$CONFIG_FILE" "$PROJECT_ROOT/CLAUDE.md"
    echo "Copied $WORKER_TYPE config to $PROJECT_ROOT/CLAUDE.md"

    cd "$PROJECT_ROOT"
    echo ""
    echo "Starting Claude Code in $PROJECT_ROOT..."
    echo "Worker type: $WORKER_TYPE"
    echo ""
fi

# Start Claude Code
exec claude
