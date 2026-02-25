# Agent Configuration - Cloud_PMS

This directory contains CLAUDE.md configurations for parallel AI workers.

## Workers

| Worker | File | Domain |
|--------|------|--------|
| Frontend | `FRONTEND_WORKER.md` | `apps/web/` - Next.js, React, UI |
| Backend | `BACKEND_WORKER.md` | `apps/api/`, `supabase/` - FastAPI, PostgreSQL |

## How to Use

### Starting a Worker Session

**Frontend Worker:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
# Copy or symlink the worker config
cp docs/AGENTS/FRONTEND_WORKER.md CLAUDE.md
# Start Claude Code session
claude
```

**Backend Worker:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
# Copy or symlink the worker config
cp docs/AGENTS/BACKEND_WORKER.md CLAUDE.md
# Start Claude Code session
claude
```

### Git Worktrees (Recommended)

For true isolation, use git worktrees:
```bash
# Create frontend worktree
git worktree add ../cloud_pms_frontend -b feature/frontend-work

# Create backend worktree
git worktree add ../cloud_pms_backend -b feature/backend-work

# Copy appropriate CLAUDE.md to each
cp docs/AGENTS/FRONTEND_WORKER.md ../cloud_pms_frontend/CLAUDE.md
cp docs/AGENTS/BACKEND_WORKER.md ../cloud_pms_backend/CLAUDE.md
```

## Coordination

Workers communicate via `.planning/` directory:

```
.planning/
├── frontend-requests/    # Frontend requesting backend changes
├── backend-requests/     # Backend notifying frontend of changes
└── shared/               # Cross-team documentation
```

### Request Format

```markdown
## Request: [Title]
**Date:** YYYY-MM-DD
**Priority:** high/medium/low
**Status:** pending/in-progress/completed

### Description
[What is needed]

### Blocker
[What work is blocked without this]

### Proposed Solution
[Suggested implementation]
```

## Plugin Requirements

### Frontend Worker
- frontend-design
- typescript-lsp
- playwright
- context7
- superpowers
- code-review

### Backend Worker
- supabase
- context7
- superpowers
- code-review
- security-guidance

## Boundaries Summary

| Path | Frontend | Backend |
|------|----------|---------|
| `apps/web/` | WRITE | READ |
| `apps/api/` | READ | WRITE |
| `supabase/` | READ | WRITE |
| `database/` | READ | WRITE |
| `migrations/` | READ | WRITE |
| `.env.*` | COORDINATE | COORDINATE |
| `docker-compose.*` | COORDINATE | COORDINATE |

## Merge Strategy

1. Each worker creates PRs to `main`
2. Frontend PRs should not touch backend files
3. Backend PRs should not touch frontend files
4. CI validates boundaries via CODEOWNERS (if configured)

## Conflict Prevention

- Workers announce major changes in `.planning/`
- API contract changes require coordination
- Database schema changes require frontend notification
- Shared dependencies require discussion
