# Repo Touchpoints (Where engineers should look first)

Based on current references:
- Middleware: `apps/api/middleware/auth.py`
  - JWT verification
  - membership resolution (MASTER)
  - role resolution (TENANT)
  - context construction (must become the single source of truth)

- TENANT helpers/migrations:
  - `supabase/migrations/*helpers*`
  - storage policy migrations
  - table RLS patterns

- Tests:
  - `tests/docker/run_rls_tests.py`
  - `tests/ci/*acceptance*.py`

## Required refactors
- Create a single `request_context` module used everywhere.
- Create a single `ownership_validation` module used in every handler.
- Create a single `cache_key` builder used by streaming and search.

Update this file as paths evolve. The key is: reduce “tribal knowledge”.
