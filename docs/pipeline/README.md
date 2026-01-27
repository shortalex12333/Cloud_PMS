# Celeste Pipeline: Lens → Code → Tests → Verify

## Purpose

Build operational flows from a gold "lens" spec into production-grade code with DB/RLS guarantees.

**Pipeline:** Document → Tests → Code → Verify

**Principle:** Backend defines actions, signatures, and RLS. Frontend renders what backend returns.

---

## Status (After Certificates Lens)

| Component | Status | Notes |
|-----------|--------|-------|
| Backend endpoint | ✅ Complete | `GET /v1/actions/list` with role-gating |
| Action registry | ✅ Complete | 5 certificate actions with domain/variant/search |
| Storage semantics | ✅ Complete | 3 file actions with bucket/path config |
| Docker tests | ✅ 18/18 pass | Role gating, CRUD, isolation, edge cases |
| Staging CI | ✅ Pass | Real JWT validation |
| Frontend integration | ✅ Complete | SuggestedActions + ActionModal |
| Build | ✅ Pass | TypeScript compiles |

**Tag:** `cert-lens-gold`

---

## Key Files (Verified)

### Backend
- `apps/api/routes/p0_actions_routes.py` - Action endpoints (NOT router.py)
- `apps/api/action_router/registry.py` - Action definitions + search
- `tests/docker/run_rls_tests.py` - Role-gating tests

### Frontend
- `apps/web/src/components/SuggestedActions.tsx` - Action buttons
- `apps/web/src/components/actions/ActionModal.tsx` - Execution modal
- `apps/web/src/hooks/useCelesteSearch.ts` - Intent detection

See `FILE_MAP.md` for complete list.

---

## Guardrails (Non-Negotiable)

| Rule | Enforcement |
|------|-------------|
| Backend authority | Frontend calls `/v1/actions/list`, never invents actions |
| RLS everywhere | `get_user_yacht_id()` in all queries |
| Role gating | `allowed_roles` in registry matches RLS policies |
| Signature invariant | `pms_audit_log.signature` is `{}` or JSON, never NULL |
| Storage isolation | Paths start with `{yacht_id}/` |
| No UI authority | Frontend only renders what backend returns |

---

## For Next Lens

1. Read `LESSONS_LEARNED.md` first (what went wrong)
2. Follow `NEXT_AGENT.md` step-by-step
3. Use `ACCEPTANCE_MATRIX.md` for test expectations
4. Run commands from `RUNBOOK.md`

---

## Quick Reference

```bash
# Backend tests
cd apps/api && python3 -m pytest tests/docker/run_rls_tests.py -v

# Frontend build
cd apps/web && npm run build

# Full verify
cd apps/web && npx tsc --noEmit && npm run build
```
