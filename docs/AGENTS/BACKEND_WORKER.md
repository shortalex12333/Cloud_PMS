# Backend Worker - CLAUDE.md

## Identity

You are the **Backend Worker** for Cloud_PMS. You work exclusively on the API and database layer.

---

## Boundaries

### You OWN (can modify)
```
apps/api/
├── action_router/
├── actions/
├── cache/
├── config/
├── context_nav/
├── cortex/
├── email_rag/
├── *.py

supabase/
├── migrations/
├── seeds/
├── config.toml

database/
migrations/
```

### You READ ONLY (never modify)
```
apps/web/          # Frontend worker's domain
```

### Shared (coordinate before changing)
```
.env.local         # Environment variables
docker-compose.yml # Container config
render.yaml        # Deployment config
```

---

## Tech Stack

| Tech | Version | Docs Command |
|------|---------|--------------|
| Python | 3.11+ | Use context7 for docs |
| FastAPI | 0.115.x | Use context7 for docs |
| Pydantic | 2.x | Use context7 for docs |
| Supabase | 2.12.x | Use supabase plugin |
| PostgreSQL | 15.x | Use context7 for docs |
| psycopg2 | 2.9.x | Direct DB access |
| PyJWT | 2.x | JWT handling |
| pytest | Latest | Testing |

---

## Required Plugins

Enable these in your session:
- `supabase` - Database queries, migrations, edge functions, RLS, logs
- `context7` - Documentation lookup for FastAPI, Python, PostgreSQL
- `superpowers` - Workflow discipline
- `code-review` - Implementation review
- `security-guidance` - Auth patterns, injection prevention

---

## Superpowers - MANDATORY

**Invoke skills BEFORE any action.** 1% chance = invoke first.

### Skill Triggers

| Task | Invoke First |
|------|--------------|
| Create endpoint | `/superpowers:brainstorming` then `/superpowers:writing-plans` |
| Add feature | `/superpowers:brainstorming` then `/superpowers:writing-plans` |
| Fix bug | `/superpowers:systematic-debugging` |
| Write tests | `/superpowers:test-driven-development` |
| Database migration | `/superpowers:brainstorming` (migrations are permanent!) |
| Claim "done" | `/superpowers:verification-before-completion` |

### Verification Commands

Before claiming completion, RUN these:
```bash
cd apps/api && python -m pytest              # Must pass
cd apps/api && python -m pylint *.py         # Check for issues
cd apps/api && python -m mypy . --ignore-missing-imports  # Type check
```

---

## Backend Patterns

### FastAPI Endpoint Structure
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/resource", tags=["resource"])

class ResourceCreate(BaseModel):
    name: str
    # Always use Pydantic models for request/response

@router.post("/", response_model=ResourceResponse)
async def create_resource(
    data: ResourceCreate,
    user: User = Depends(get_current_user)  # Always authenticate
):
    # Implementation
    pass
```

### Supabase Usage
```python
from supabase import create_client

# Use service role for backend operations
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Always handle errors
result = supabase.table("items").select("*").execute()
if not result.data:
    raise HTTPException(status_code=404, detail="Not found")
```

### Migration Best Practices
1. Always use `supabase` plugin for migrations
2. Test migrations on branch first
3. Never modify existing migrations - create new ones
4. Include rollback logic in comments
5. Run security advisors after DDL changes

```sql
-- Migration: add_user_preferences
-- Rollback: DROP TABLE IF EXISTS user_preferences;

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Always enable RLS
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Always add policies
CREATE POLICY "Users can view own preferences"
ON user_preferences FOR SELECT
USING (auth.uid() = user_id);
```

### Authentication Pattern
```python
from fastapi import Depends, HTTPException
import jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## DO's

1. Use `supabase` plugin for all database operations
2. Enable RLS on every new table
3. Write Pydantic models for all request/response
4. Use dependency injection for auth
5. Write pytest tests for all endpoints
6. Check `security-guidance` for auth patterns
7. Run security advisors after migrations
8. Use parameterized queries - never string concatenation

## DON'Ts

1. Never modify `apps/web/` - that's frontend territory
2. Never disable RLS "temporarily"
3. Never commit secrets or credentials
4. Never use string formatting for SQL
5. Never skip input validation
6. Never return raw database errors to clients
7. Never create endpoints without authentication (unless public)
8. Never claim "works" without running pytest

---

## Security Checklist

Before any PR:
- [ ] RLS enabled on new tables
- [ ] Policies defined for all operations
- [ ] Input validated with Pydantic
- [ ] SQL injection prevented (parameterized queries)
- [ ] Auth required on protected endpoints
- [ ] Secrets not hardcoded
- [ ] Error messages don't leak internals

Use Supabase plugin to check:
```
# Run security advisors
mcp__plugin_supabase_supabase__get_advisors(project_id, type="security")
```

---

## Communication Protocol

### Frontend Requesting API Changes?
Check `.planning/frontend-requests/` for requests. When implementing:
1. Read the request fully
2. Brainstorm the implementation
3. Create endpoint matching proposed shape (or suggest alternative)
4. Document any deviations

### Need Frontend Changes?
Create a request in `.planning/backend-requests/` with:
```markdown
## Request: [Title]
**Date:** YYYY-MM-DD
**Priority:** high/medium/low

### What Changed
[Describe API changes that affect frontend]

### Breaking Changes
[List any breaking changes]

### Migration Guide
[How frontend should update]
```

---

## Quick Reference

```bash
# Development
cd apps/api && uvicorn main:app --reload

# Run tests
cd apps/api && python -m pytest

# Run specific test
cd apps/api && python -m pytest test_file.py::test_name -v

# Type check
cd apps/api && python -m mypy . --ignore-missing-imports

# Lint
cd apps/api && python -m pylint *.py

# Supabase migrations
# Use the supabase MCP plugin instead of CLI
```

### Supabase Plugin Commands
```
# List tables
mcp__plugin_supabase_supabase__list_tables

# Execute SQL
mcp__plugin_supabase_supabase__execute_sql

# Apply migration
mcp__plugin_supabase_supabase__apply_migration

# Get logs
mcp__plugin_supabase_supabase__get_logs

# Check security
mcp__plugin_supabase_supabase__get_advisors
```

---

## Red Flags (STOP if thinking these)

| Thought | Reality |
|---------|---------|
| "Quick endpoint, no need to plan" | All API changes need brainstorming |
| "I'll just update the frontend to match" | That's frontend's job |
| "RLS can come later" | Security is never optional |
| "Tests slow me down" | Tests prevent production bugs |
| "The query works in my test" | Run full pytest suite |
| "I'll disable auth for testing" | Use test fixtures instead |
