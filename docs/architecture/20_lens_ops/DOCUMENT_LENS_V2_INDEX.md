# Document Lens v2 - Operations Index

**Tag:** `document-lens-gold`
**Status:** Conditional Greenlight
**Last Updated:** 2026-01-28

---

## Quick Navigation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [FINAL_SIGNOFF.md](./DOCUMENT_LENS_V2_FINAL_SIGNOFF.md) | Pre-deployment checklist | Before production deploy |
| [OPS.md](./DOCUMENTS_LENS_OPS.md) | Architecture & monitoring | Understanding the system |
| [WORKER_DEPLOYMENT.md](./WORKER_DEPLOYMENT_GUIDE.md) | Render setup guide | Deploying health worker |
| [OBSERVABILITY.md](./OPS_OBSERVABILITY.md) | SLOs & alerts | Setting up monitoring |
| [BACKLOG_EVIDENCE.md](./EXTENDED_BACKLOG_EVIDENCE.md) | Implementation audit trail | Verification |

---

## Current State

### Completed
- Staging Documents Acceptance: 17/17 pass
- Stress Test: 0×500 errors
- Schema migrations prepared
- Security audit script created
- Two-phase mutation infrastructure designed

### Pending (Manual)
- [ ] Apply migrations to tenant DB
- [ ] Deploy health worker via Render
- [ ] Run smoke tests
- [ ] Merge to main

---

## Related Files

### Migrations
```
supabase/migrations/20260128_doc_metadata_soft_delete.sql
supabase/migrations/20260128_staged_mutations.sql
```

### Scripts
```
scripts/preflight/check_doc_metadata_schema.py
scripts/security/audit_service_role_usage.py
```

### Worker
```
tools/ops/monitors/documents_health_worker.py
```

---

## Sign-Off Workflow

```
1. Read DOCUMENT_LENS_V2_FINAL_SIGNOFF.md
2. Apply migrations (commands provided)
3. Deploy worker (Render steps provided)
4. Run smoke tests (curl commands provided)
5. Verify all checkboxes complete
6. Merge PR: security/signoff → main
7. Tag: document-lens-v2-production
```
