# Certificate Lens — Complete Codebase Audit
**Generated:** 2026-04-19  
**Branch:** `main` @ `63eeeb0f`  
**Scope:** Every file that touches the certificate lens — frontend, backend, types, tests, migrations, CI, cross-domain dependencies, styling, and indirect effects.

---

## Table of Contents

1. [Complete File Inventory](#1-complete-file-inventory)
2. [Request Chain — Full Trace](#2-request-chain--full-trace)
3. [Critical Issues](#3-critical-issues-fix-before-next-deploy)
4. [Silent Error Swallowing](#4-silent-error-swallowing)
5. [Weak & Missing Types](#5-weak--missing-types)
6. [Dead, Duplicate & Legacy Code](#6-dead-duplicate--legacy-code)
7. [DRY Analysis](#7-dry-analysis)
8. [Cross-Domain Dependencies](#8-cross-domain-dependencies)
9. [Where to Enter the Repo for Any Change](#9-where-to-enter-the-repo-for-any-change)

---

## 1. Complete File Inventory

### 1A. Frontend — 34 Files

#### Core Certificate Files (cert-specific logic lives here)

| File | LOC est. | Role |
|------|----------|------|
| `apps/web/src/components/lens-v2/entity/CertificateContent.tsx` | ~520 | **Primary cert lens component.** Renders all 9 sections (Identity, Holder's Certs, Coverage, Renewal History, Notes, Attachments, Audit Trail, Related Certs, History). Drives the split-button primary action and chevron dropdown. Owns `pendingRenew` two-step upload state. Hardcodes SigL2 downgrade from SigL3 (lines 140–141). |
| `apps/web/src/app/certificates/page.tsx` | ~200 | **Certificates list page** (`/certificates`). Hosts `FilteredEntityList` with `certAdapter`, fetches action list, manages `EntityDetailOverlay`. Defines inline `Certificate` and `RegistryAction` TypeScript interfaces (not shared). |
| `apps/web/src/app/certificates/register/page.tsx` | ~180 | **Printable compliance register** (`/certificates/register`). Groups certs by urgency tier (expired, expiring_30, expiring_90, valid, terminal). Targets port state control / surveyor visits. Print-only CSS, no global overrides. |

#### Entity Lens Framework (shared by all 13 entity types, cert is one consumer)

| File | Role |
|------|------|
| `apps/web/src/components/lens-v2/EntityLensPage.tsx` | Wrapper for ALL entity detail pages. Provides `EntityLensProvider`, renders glass header, intercepts signature actions, manages `RelatedDrawer` and ledger history sidebar. |
| `apps/web/src/components/lens-v2/ActionPopup.tsx` | Universal action modal. Renders signature levels 0–5 (silent / confirm / name-attestation / PIN / wet-sig / approval-chain). Auto-builds form fields from `field_schema`. |
| `apps/web/src/components/lens-v2/mapActionFields.ts` | Converts backend `field_schema` → `ActionPopup` field array. Also exports `getSignatureLevel()` and `actionHasFields()`. Generic — no cert-specific logic. |
| `apps/web/src/contexts/EntityLensContext.tsx` | React Context providing `entity`, `availableActions`, `executeAction`, `getAction`, `refetch`, `isLoading`, `error`. |
| `apps/web/src/hooks/useEntityLens.ts` | Data fetching hook. Calls `GET /v1/entity/{type}/{id}`, caches `available_actions`. Abort controller on unmount. |
| `apps/web/src/components/lens-v2/IdentityStrip.tsx` | Header: overline ID, title, context line, pills, detail rows. Fully generic — no domain logic. Line 56: renders `<span />` when no overline (keeps action button top-right). |
| `apps/web/src/components/lens-v2/SplitButton.tsx` | Primary action button with Radix UI dropdown. Supports disabled state, danger items (red), tooltips. |
| `apps/web/src/components/lens-v2/LensGlassHeader.tsx` | Glass/frosted header bar at top of lens page. |
| `apps/web/src/components/lens-v2/RelatedDrawer.tsx` | Side drawer: related entities via semantic search. Signal-driven via `useSignalRelated()`. |
| `apps/web/src/components/lens-v2/ScrollReveal.tsx` | Intersection Observer wrapper for lazy section reveal. Wraps all major lens sections in CertificateContent. |
| `apps/web/src/components/lens-v2/LensPill.tsx` | Status / tag pill (blue, green, red, amber). Used by IdentityStrip. |
| `apps/web/src/components/lens-v2/CollapsibleSection.tsx` | Section header with collapse toggle and optional action button. |

#### Section Components (generic, used by cert and all other lenses)

| File | Role |
|------|------|
| `apps/web/src/components/lens-v2/sections/NotesSection.tsx` | Note timeline — author, timestamp, body, "show more". |
| `apps/web/src/components/lens-v2/sections/AttachmentsSection.tsx` | File list — mime icon, name, size, download link. |
| `apps/web/src/components/lens-v2/sections/AuditTrailSection.tsx` | Audit event timeline — action, actor, timestamp. |
| `apps/web/src/components/lens-v2/sections/DocRowsSection.tsx` | Linked entity rows — icon, name, code, metadata. Used for Related Certs and Holder's Certs. |
| `apps/web/src/components/lens-v2/sections/KVSection.tsx` | Generic key-value table section. Used for Coverage Details. |
| `apps/web/src/components/lens-v2/sections/HistorySection.tsx` | Compliance period history — year/label/status/summary. |
| `apps/web/src/components/lens-v2/sections/index.ts` | Barrel export for all section components. |

#### Action Modals

| File | Role |
|------|------|
| `apps/web/src/components/lens-v2/actions/AddNoteModal.tsx` | Text note modal. 2000-char limit, toast on success, Escape to dismiss. Used by cert and other lenses. |
| `apps/web/src/components/lens-v2/actions/AttachmentUploadModal.tsx` | File upload modal. Two modes: direct Supabase write (`bucket="pms-certificate-documents"`, `category="certificate"`) or caller-provided strategy. `pendingRenew` flow triggers this first, then the renew popup. |

#### List & Filter Infrastructure

| File | Role |
|------|------|
| `apps/web/src/features/entity-list/components/FilteredEntityList.tsx` | Generic list: FilterPanel + sorted/paginated results. Used by cert list page with `domain="certificates"`. |
| `apps/web/src/features/entity-list/components/EntityDetailOverlay.tsx` | Side panel drawer for entity detail. Used to show cert detail in overlay from list page. |
| `apps/web/src/features/entity-list/hooks/useFilteredEntityList.ts` | Data fetching for filtered list. For certs, queries `v_certificates_enriched`. |

#### Styling

| File | Role |
|------|------|
| `apps/web/src/components/lens-v2/lens.module.css` | CSS module for all lens-v2 components. All values are semantic tokens (`--mark`, `--txt`, `--red-bg`). **No hardcoded colour values.** |
| `apps/web/src/components/lens-v2/popup.module.css` | ActionPopup and signature level styles. Token-based. |

#### Types

| File | Role |
|------|------|
| `apps/web/src/types/entity.ts` | `EntityType` union (13 types incl. `'certificate'`), `AvailableAction`, `ActionResult`. |
| `apps/web/src/types/actions.ts` | `ACTION_DISPLAY` map: icon + cluster per action_id. Only `update_certificate` has an explicit entry — all other cert actions fall back to generic `{ icon: 'circle', cluster: 'entity' }`. |

#### Navigation & Utilities

| File | Role |
|------|------|
| `apps/web/src/components/shell/Sidebar.tsx` | Left sidebar. "Certificates" item at line 90, under Compliance group. |
| `apps/web/src/lib/entityRoutes.ts` | `getEntityRoute(entityType, id)` — URL generator. Used by CertificateContent for navigation links. |
| `apps/web/src/components/shell/VesselSurface.tsx` | Dashboard surface widget. Shows expiring certs widget — `SurfaceCertificate { id, name, daysRemaining, status }`, sourced from `liveData?.certificates_expiring?.items`. Severity badge: `'warning'` if any cert expiring < 30 days. |

---

### 1B. Backend — 14 Files

| File | LOC | Role |
|------|-----|------|
| `apps/api/handlers/certificate_handlers.py` | ~1,672 | **Single source of truth for all cert operations.** `CertificateHandlers` class + 14 adapters. All mutations + reads live here. |
| `apps/api/action_router/registry.py` | ~4,561 | Global action registry. Contains 14 cert action definitions. |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | ~4,240 | Main dispatcher. Contains 10 cert wrapper functions + `INTERNAL_HANDLERS` dict. |
| `apps/api/routes/entity_routes.py` | ~1,231 | `GET /v1/entity/certificate/{id}` — two-table lookup, attachment/notes/audit assembly. |
| `apps/api/routes/certificate_routes.py` | ~477 | **Legacy / feature-gated.** REST endpoints (`GET /vessel`, `GET /crew`, `GET /details/{id}`, `GET /expiring`, `POST /pipeline-test`). Gated by `FEATURE_CERTIFICATES` env var. Unclear if still registered. |
| `apps/api/routes/handlers/certificate_phase4_handler.py` | ~100 | **Pass-through shim.** 5 Phase 4 actions (create-vessel, create-crew, update, link-document, supersede) that immediately delegate to `certificate_handlers.py`. Adds zero logic. |
| `apps/api/action_router/validators/rls_entity_validator.py` | ~141 | RLS entity ownership validation. Line 28: `"certificate_id": "v_certificates_enriched"` — uses UNION view for both vessel + crew. |
| `apps/api/handlers/schema_mapping.py` | ~148 | Table name resolution: `"vessel_certificates"` → `"pms_vessel_certificates"`. |
| `apps/api/action_router/ledger_metadata.py` | ~128 | Ledger safety net event-type mappings for 11 cert actions. |
| `apps/api/routes/vessel_surface_routes.py` | — | References `v_certificates_enriched` for register/surface view data. |
| `apps/api/services/entity_serializer.py` | — | Entity serialization — likely renders certs in list API responses. |
| `apps/api/action_router/router.py` | — | Entry point for `POST /v1/actions/execute`. Validates JWT, role, yacht isolation, required fields before dispatch. |
| `apps/api/middleware/auth.py` | — | JWT auth middleware, provides `get_authenticated_user()`. |
| `apps/api/integrations/supabase.py` | — | DB client factory, provides `get_supabase_client()` and `get_tenant_client()`. |

### 1C. Cross-Cutting Files

| File | Role |
|------|------|
| `tests/e2e/certificate_runner.py` | Standalone Playwright runner — 17 scenarios + 4 edge cases. Uses `CERT04-RUN-` prefix for cleanup. Targets `app.celeste7.ai`. |
| `apps/api/tests/cert_binary_tests.py` | Python unit tests — direct Supabase client calls. Covers renew, archive, suspend, status transitions, audit trail, ledger events. |
| `apps/web/e2e/shard-31-fragmented-routes/route-certificates.spec.ts` | Route-level acceptance tests. |
| `apps/web/e2e/shard-33-lens-actions/certificate-actions.spec.ts` | Lens actions — basic. |
| `apps/web/e2e/shard-34-lens-actions/certificate-actions-full.spec.ts` | Lens actions — comprehensive. |
| `apps/web/e2e/shard-43-docs-certs/docs-certs-actions.spec.ts` | Documents + certs integration. |
| `apps/web/e2e/shard-53-certificate-e2e/certificate-e2e.spec.ts` | Full end-to-end suite. |
| `apps/api/tests/test_entity_endpoints.py` | `TestCertificateEntity` class — 3 tests. **Note:** `test_200_returns_correct_shape` is broken (mock mismatch, pre-existing since PR #393). |
| `.github/workflows/staging-certificates-acceptance.yml` | CI workflow. **BROKEN — references `tests/ci/staging_certificates_acceptance.py` which does NOT exist.** |
| `apps/api/config/env.py` | Feature flags `FEATURE_CERTIFICATES` + `UI_CERTIFICATES`. Both default `False`. Confusingly grouped under `FaultLensSettings`. |
| `apps/api/config/projection.yaml` | Projection config for `certificates` + `crew_certificates` entity types. Quick filters for `certificate_type` and `days_until_expiry`. |
| `supabase/migrations/` | Directory exists but contains only `.gitkeep` — **no migration files committed** (migrations applied directly via Supabase console, per project convention). |
| `docs/ongoing_work/certificates/CERTIFICATE_SCENARIO_CHECKLIST.md` | v3 test checklist — current, maintained. |
| `docs/ongoing_work/certificates/CERTIFICATE_MANUAL_TEST_LOG.md` | Manual test log — current. |
| `apps/web/public/prototypes/lens-certificate.html` | Static HTML prototype used as design reference. Not loaded at runtime. |
| `docs/explanations/LENS_DOMAINS/certificates.md` | Domain explanation doc. Notes handover coupling risk explicitly. |

---

## 2. Request Chain — Full Trace

### A. Action Execution: `POST /v1/actions/execute` → `suspend_certificate`

```
CLIENT
  │
  ▼ POST /v1/actions/execute
  │   { action_id: "suspend_certificate", yacht_id, entity_id, reason, signature: { method: "name", name: "..." } }
  │
  ▼ apps/api/action_router/router.py:87 — execute_action()
  │   1. validate_jwt()                    — extract user context from Bearer token
  │   2. validate_yacht_isolation()        — user's yacht_id must match payload yacht_id
  │   3. validate_role_permission()        — user.role in ["captain", "manager"] (from registry)
  │   4. validate_required_fields()        — yacht_id, entity_id, reason, signature all present
  │   5. validate_payload_entities()       — calls rls_entity_validator.py:28
  │      └── SELECT id FROM v_certificates_enriched WHERE id=$entity_id AND yacht_id=$yacht_id
  │          (UNION view: pms_vessel_certificates ∪ pms_crew_certificates)
  │
  ▼ apps/api/action_router/dispatchers/internal_dispatcher.py:439
  │   INTERNAL_HANDLERS["suspend_certificate"] → _cert_suspend()
  │   └── handlers.get("suspend_certificate") from certificate_handlers.py
  │
  ▼ apps/api/handlers/certificate_handlers.py:1397
  │   _change_certificate_status_adapter("suspended")
  │   1. _resolve_cert_domain()            — try pms_vessel_certificates, fallback to pms_crew_certificates
  │   2. _cert_mutation_gate()             — narrow role check by domain
  │   3. DB UPDATE pms_vessel_certificates SET status="suspended", properties={reason, suspended_by, ...}
  │   4. DB INSERT pms_audit_log {action, entity_id, user_id, signature_payload, ...}  ← try/except: pass (!)
  │   5. _notify_cert_stakeholders()       — DB INSERT pms_notifications ×N recipients
  │   6. return { status: "success", new_status: "suspended", certificate_id, reason }
  │
  ▼ LEDGER SAFETY NET (if handler did NOT set _ledger_written=True)
  │   apps/api/action_router/ledger_metadata.py:76
  │   DB INSERT ledger_events { event_type: "status_change", entity_type: "certificate", ... }
  │
  ▼ RESPONSE → ActionResponse { success: true, data: {...} }
```

### B. Entity Detail: `GET /v1/entity/certificate/{id}`

```
CLIENT
  │
  ▼ GET /v1/entity/certificate/{cert_id}?yacht_id={yacht_id}
  │
  ▼ apps/api/routes/entity_routes.py:99 — get_certificate_entity()
  │   1. resolve_yacht_id(auth, yacht_id)
  │   2. get_tenant_client(tenant_key)
  │   3. SELECT * FROM pms_vessel_certificates WHERE id=$cert_id AND yacht_id=$yacht_id LIMIT 1
  │      ├── IF rows: domain = "vessel"
  │      └── ELSE: SELECT * FROM pms_crew_certificates WHERE id=$cert_id AND yacht_id=$yacht_id LIMIT 1
  │              ├── IF rows: domain = "crew"
  │              └── ELSE: raise 404
  │   4. Query pms_attachments WHERE entity_id=$cert_id
  │   5. Query doc_metadata WHERE id=$data.document_id (if FK present)
  │   6. Query pms_notes WHERE certificate_id=$cert_id ORDER BY created_at DESC
  │   7. Query pms_audit_log WHERE entity_type="certificate" AND entity_id=$cert_id LIMIT 50
  │   8. get_available_actions("certificate", entity_data, user.role)
  │      └── certificate_handlers._get_certificate_actions()
  │
  ▼ RESPONSE → { id, name, domain, status, attachments, notes, audit_trail, available_actions, ... }
```

### C. Phase 4 Native Routes (bypass action_router — create/update/link-doc/supersede)

```
POST /v1/certificates/create-vessel (or create-crew, update, link-document, supersede)
  │
  ▼ apps/api/routes/handlers/certificate_phase4_handler.py
  │   _enforce_rbac()    ← REDUNDANT: role already checked by router.py for /v1/actions/execute
  │   _delegate()        ← immediately calls get_certificate_handlers().get(action_id)
  │
  ▼ apps/api/handlers/certificate_handlers.py (same as /v1/actions/execute path)
```

> **Architecture note:** There are two dispatcher paths to the same handlers. The Phase 4 shim was created during migration from custom routes to `/v1/actions/execute`. The migration is incomplete — `create_vessel_certificate` and `create_crew_certificate` still use custom endpoints in the registry.

---

## 3. Critical Issues (Fix Before Next Deploy)

### 🔴 CRITICAL-1: CI workflow references non-existent test file

**File:** `.github/workflows/staging-certificates-acceptance.yml:44`  
**Problem:** Runs `python tests/ci/staging_certificates_acceptance.py` — this file does not exist. Workflow fails every run.  
**Fix options:**
- Option A: Create `tests/ci/staging_certificates_acceptance.py` as a thin wrapper that calls `certificate_runner.py`
- Option B: Repoint the workflow to `tests/e2e/certificate_runner.py` (the maintained runner)  
**Impact:** Every push to main triggers a guaranteed CI failure. Masks real failures.

### 🔴 CRITICAL-2: SigL2 downgrade is a frontend policy (not backend truth)

**File:** `apps/web/src/components/lens-v2/entity/CertificateContent.tsx:140–141`  
```typescript
// PROBLEM: Certificate domain hardcodes a downgrade.
// If the backend ever sends sigLevel=3 (PIN), this component silently overrides it to sigLevel=2 (name).
const certSigLevel: 0|1|2|3|4|5 = sigLevel === 3 ? 2 : sigLevel as 0|1|2|3|4|5;
```
**Problem:** Policy is embedded in the component. If a future cert action genuinely requires PIN (SigL3), this component will silently downgrade it without any visible error. The backend should emit the correct sig level; the frontend should not override.  
**Correct fix:** Add `"signature_level": 2` to the cert action definitions in the registry, and remove this override.  
**Why not removed yet:** Expedient fix for overnight session. Needs a registry update + removal of the cast.

---

## 4. Silent Error Swallowing

These are the most dangerous category — failures vanish with no log, no alert, no user feedback.

### Backend — `certificate_handlers.py`

| Line | Pattern | What Is Silently Lost |
|------|---------|----------------------|
| 108 | `except Exception: pass` | Ledger read fire-and-forget — audit trail for view operations may not persist |
| 144 | `except Exception: pass` | `refresh_certificate_expiry()` — expiry status in DB may be permanently stale after status change |
| 230 | `except Exception: pass` | Same as 144, for crew certs |
| 573 | `except Exception: return False` | `_is_expiring_soon()` — malformed expiry dates silently treated as "not expiring" |
| 586 | `except Exception: return False` | `_is_expired()` — malformed dates silently treated as "not expired" — certs that SHOULD show as expired do not |
| 600 | `except Exception: return None` | `_days_until_expiry()` — invalid dates return None, UI may show blank or wrong urgency |
| 854 | `except Exception: pass` | Audit insert on `create_vessel_certificate` — creation is logged to DB but audit trail is silently skipped |
| 896 | `except Exception: pass` | Document lookup on cert detail — linked doc silently missing from response |
| 920 | `except Exception: pass` | Audit insert on `link_document_to_certificate` |
| 1010 | `except Exception: pass` | Audit insert on `update_certificate` |
| 1242 | `except Exception: pass` | Audit insert on `supersede_certificate` |
| 1384 | `except Exception: pass` | Audit insert on `renew_certificate` |
| 1449 | `except Exception: pass` | Audit insert on `suspend_certificate` and `revoke_certificate` |
| 1510 | `except Exception: pass` | Audit insert on `archive_certificate` |
| 1671–1672 | `return 0` on notification error | Notification fan-out fails silently — stakeholders receive no alert |

**Pattern:** Every `except Exception: pass` on an audit insert means a cert action can succeed (DB row updated, user sees success) but leave NO audit trail. This is a compliance gap — the system is designed to be auditable but the writes are best-effort.

**What to keep:** The primary mutation (status update, create, etc.) should never be rolled back due to an audit failure. The correct pattern is to log the failure explicitly:
```python
# CORRECT: distinguish "acceptable failure" from "silent failure"
except Exception as e:
    logger.error(f"[certificate] AUDIT INSERT FAILED for {action_id} on {cert_id}: {e}")
    # Do NOT raise — primary mutation succeeded. But log it loudly.
```

**What to change:** Replace every `except Exception: pass` with `except Exception as e: logger.error(...)`.

### Frontend — `apps/web/src/app/certificates/page.tsx:107–109`

```typescript
// PROBLEM: Silently swallows action list fetch failure.
// User sees no "New Certificate" button with no explanation.
try {
  const actions = await fetchActions();
} catch {
  // silent — button just doesn't appear
}
```
**What to keep:** Not crashing the page on permission check is correct.  
**What to change:** Add a `logger.warn` or console.warn so developers see it during debugging. The UX can remain graceful.

---

## 5. Weak & Missing Types

### Frontend — `CertificateContent.tsx`

| Line | Pattern | Problem | Correct Type |
|------|---------|---------|--------------|
| 85 | `entity as Record<string, unknown>` | Suppresses all field access checks | Should be `CertificateEntity` interface matching `/v1/entity/certificate/{id}` response shape |
| 101 | `entity?.holder_certs as Array<Record<string, unknown>>` | No type on array items | `Array<{ id: string; certificate_type: string; status: string; ... }>` |
| 116–123 | Multiple `as Record<string, unknown>` casts | All suppress compiler | Define `CertificateEntityDetail` interface with all known fields |
| 138 | `action as any` in openActionPopup call | Bypasses signature check | `AvailableAction` (already defined in `types/entity.ts`) |
| 139 | `as any` on sigLevel | Loses discriminated union | `0|1|2|3|4|5` (already used on line 141) |
| 246 | `as any` in executeAction | Bypasses payload check | Define `CertificateActionPayload` union type |

**Root cause:** `AvailableAction` in `types/entity.ts` is defined generically. The actual runtime response from `/v1/entity/certificate/{id}` returns richer fields (`field_schema`, `prefill`, `confirmation_message`). The interface should be extended:

```typescript
// Current (too loose):
interface AvailableAction {
  action_id: string;
  label: string;
  requires_signature: boolean;
}

// Correct (matches actual runtime response):
interface AvailableAction {
  action_id: string;
  label: string;
  requires_signature: boolean;
  required_fields: string[];
  optional_fields: string[];
  field_schema: FieldSchemaDef[];
  prefill: Record<string, unknown>;
  confirmation_message: string | null;
  disabled_reason: string | null;
  is_primary: boolean;
  signature_level?: number;
}
```

### Frontend — `apps/web/src/types/actions.ts`

Missing `ACTION_DISPLAY` entries for cert actions. Falls back to `{ icon: 'circle', cluster: 'entity' }`:
- `renew_certificate` — should be `{ icon: 'refresh', cluster: 'entity' }`
- `suspend_certificate` — should be `{ icon: 'pause', cluster: 'entity' }`
- `archive_certificate` — should be `{ icon: 'archive', cluster: 'entity' }`
- `revoke_certificate` — should be `{ icon: 'ban', cluster: 'entity' }`
- `create_vessel_certificate` — should be `{ icon: 'plus', cluster: 'create' }`
- `create_crew_certificate` — should be `{ icon: 'plus', cluster: 'create' }`

### Backend — `certificate_handlers.py`

| Function | Missing Type | Correct Annotation |
|----------|-------------|-------------------|
| `_resolve_cert_domain()` | No return type | `-> tuple[str, dict] | tuple[None, None]` |
| `_cert_mutation_gate()` | No return type | `-> None` (raises on failure) |
| `_is_expiring_soon()` | No type hints | `(expiry_date: str | None) -> bool` |
| `_is_expired()` | No type hints | `(expiry_date: str | None) -> bool` |
| `_days_until_expiry()` | No type hints | `(expiry_date: str | None) -> int | None` |
| `_format_changes()` | No return type | `-> list[dict[str, Any]]` |
| `_notify_cert_stakeholders()` | No return type | `-> int` (count of notifications sent) |
| All adapter functions | `**params: Dict[str, Any]` | Should be typed payload dataclasses — params is an unvalidated bag |

### Backend — `internal_dispatcher.py`

All 10 cert wrapper functions have the same untyped signature:
```python
async def _cert_suspend(params: Dict[str, Any], context: Dict[str, Any], ...):
```
The `params` dict is passed through without validation — field presence/type is checked only in the handler. This means type errors surface as runtime `KeyError` at handler time, not at dispatch time.

---

## 6. Dead, Duplicate & Legacy Code

### 6A. `certificate_phase4_handler.py` — The Useless Shim

**File:** `apps/api/routes/handlers/certificate_phase4_handler.py` (~100 lines)  
**What it does:** For 5 actions (create-vessel, create-crew, update, link-doc, supersede), it:
1. Calls `_enforce_rbac()` (DUPLICATE: router.py already checks roles)
2. Calls `_delegate()` → immediately calls `get_certificate_handlers().get(action_id)` in `certificate_handlers.py`

**It adds zero logic.** It's a migration artifact from before `/v1/actions/execute` was unified.  

**Why it still exists:** The registry entries for `create_vessel_certificate` and `create_crew_certificate` still point to custom routes (`/v1/certificates/create-vessel`, `/v1/certificates/create-crew`) rather than `/v1/actions/execute`. These custom routes hit `certificate_phase4_handler.py`.

**What "dead" means here:** The file isn't unreachable — it IS called via the custom routes. But it's architecturally redundant; the only reason it exists is that the route migration is incomplete.

**Resolution:** Change `create_vessel_certificate` and `create_crew_certificate` registry endpoints to `/v1/actions/execute`, add them to `INTERNAL_HANDLERS` in `internal_dispatcher.py`, and delete `certificate_phase4_handler.py`.

### 6B. `certificate_routes.py` — Unclear if Active

**File:** `apps/api/routes/certificate_routes.py` (~477 lines)  
**Contents:** REST endpoints predating the action_router architecture:
- `GET /vessel` — list vessel certs
- `GET /crew` — list crew certs
- `GET /details/{id}` — cert details
- `GET /expiring` — expiring certs
- `POST /pipeline-test` — debug endpoint

**Feature gating:** Line 90–92 checks `FEATURE_CERTIFICATES`. Both `FEATURE_CERTIFICATES` and `UI_CERTIFICATES` default to `False` in `env.py`.

**What to do:**
- If `FEATURE_CERTIFICATES=False` in production: this file is inactive dead code. Mark with a top-of-file comment: `# LEGACY: REST endpoints predating action_router. Gated by FEATURE_CERTIFICATES env var. Will be removed when migration to /v1/actions/execute is complete.`
- If `FEATURE_CERTIFICATES=True` in production: audit which endpoints are still called and migrate consumers.
- The `POST /pipeline-test` endpoint should be removed from all environments — debug endpoints in production code are security surface area.

### 6C. Duplicate RBAC Checks

Phase 4 path: `certificate_phase4_handler.py:46` `_enforce_rbac()` checks roles.  
Action_router path: `router.py` validates roles against registry entries.  

Both paths hit the same `certificate_handlers.py` functions. For Phase 4 routes, RBAC runs twice. This is harmless but wasteful and confusing.

### 6D. Duplicate Registry Entries for Phase 4 Actions

Actions `create_vessel_certificate` and `create_crew_certificate` appear in both:
1. Registry entries (for action discovery and display)
2. Phase 4 route handlers (for actual execution)

They're registered in `INTERNAL_HANDLERS` in `internal_dispatcher.py` (lines ~369–380) AND handled by `certificate_phase4_handler.py`. When a request comes in via `/v1/actions/execute`, it goes through `internal_dispatcher.py`. When it comes in via the custom route, it goes through `certificate_phase4_handler.py`. Both call the same underlying handler function. Two entry points, one destination.

### 6E. `test_entity_endpoints.py::TestCertificateEntity` — Broken Mock

**File:** `apps/api/tests/test_entity_endpoints.py`  
**Test:** `TestCertificateEntity::test_200_returns_correct_shape`  
**Status:** Permanently broken. The mock helper `_supabase_mock()` was written for `.maybe_single()` but `entity_routes.py` was changed to `.limit(1).execute()` in commit `239db387` (April 14). The mock returns empty data, causing a 404. The test file was last modified in PR #393 and has never been updated to match.  

**What to do:** Either update the mock or delete the test. The runner (`certificate_runner.py`) provides better coverage against real infrastructure.

> A new engineer reading this test would assume the cert entity endpoint is broken — it's not. The test is broken. Adding this comment to the test file prevents false alarm:
> ```python
> # NOTE: This test uses a .maybe_single() mock pattern but entity_routes.py
> # uses .limit(1).execute() (changed in commit 239db387 to fix AttributeError
> # on supabase client version). The mock needs updating before this test is valid.
> # See: certificate_runner.py scenario 1 for working integration coverage.
> ```

---

## 7. DRY Analysis

### 7A. Where to Consolidate (Genuine Duplication)

**Audit insert boilerplate — repeated ~8 times in certificate_handlers.py:**

```python
# This pattern appears at lines 854, 920, 1010, 1242, 1384, 1449, 1510:
try:
    db.table("pms_audit_log").insert({
        "action": "archive_certificate",
        "entity_type": "certificate",
        "entity_id": certificate_id,
        "yacht_id": yacht_id,
        "user_id": user_id,
        "new_values": {"status": "archived"},
        "signature": signature_payload,
        "created_at": datetime.utcnow().isoformat()
    }).execute()
except Exception:
    pass  # fire-and-forget
```

**Consolidate into:**
```python
def _write_cert_audit(
    db, action: str, cert_id: str, yacht_id: str, user_id: str,
    new_values: dict, signature: dict | None = None
) -> None:
    """Write to pms_audit_log. Logs error on failure but does NOT raise
    (primary mutation already committed — audit is best-effort)."""
    try:
        db.table("pms_audit_log").insert({
            "action": action, "entity_type": "certificate",
            "entity_id": cert_id, "yacht_id": yacht_id, "user_id": user_id,
            "new_values": new_values,
            "signature": signature or {},
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"[cert-audit] INSERT FAILED: {action} on {cert_id}: {e}")
```
This eliminates 8 repetitions AND fixes the silent error problem simultaneously.

**The 10 dispatcher wrappers in `internal_dispatcher.py` — boilerplate shims:**

Every cert wrapper (lines 369–460) is identical except for the action_id string:
```python
async def _cert_suspend(params, context, yacht_id, user_id, user_context, db_client):
    handlers = get_certificate_handlers(db_client)
    handler_fn = handlers.get("suspend_certificate")
    if not handler_fn:
        raise ValueError("suspend_certificate handler not registered")
    return await handler_fn(params, context, yacht_id, user_id, user_context, db_client)
```

These CAN be collapsed into a factory:
```python
def _make_cert_handler(action_id: str):
    async def _handler(params, context, yacht_id, user_id, user_context, db_client):
        handlers = get_certificate_handlers(db_client)
        handler_fn = handlers.get(action_id)
        if not handler_fn:
            raise ValueError(f"{action_id} handler not registered")
        return await handler_fn(params, context, yacht_id, user_id, user_context, db_client)
    _handler.__name__ = f"_cert_{action_id}"
    return _handler

# Replace 10 explicit functions with:
INTERNAL_HANDLERS.update({
    f"action_id": _make_cert_handler("action_id")
    for action_id in CERT_ACTIONS
})
```

**DO NOT consolidate if** the wrappers ever need different pre/post logic. Inspect each one before collapsing.

### 7B. Where NOT to Consolidate (Looks Similar, Different Purpose)

**`CertificateContent.tsx` vs `WorkOrderContent.tsx` vs `WarrantyContent.tsx`:** These all use `EntityLensPage` + `ActionPopup` + `SplitButton`. Do NOT merge them into a generic `EntityContent`. Each domain has distinct:
- Section layout (cert has Holder's Certs, Renewal History; warranty has warranty period, parts; work order has sub-tasks)
- Primary action logic (`pendingRenew` is cert-specific; warranty has `pendingApproval`; etc.)
- Dropdown filter rules (cert excludes assign/supersede; other domains have their own exclusions)

**`_cert_mutation_gate()` vs `_hor_mutation_gate()` vs `_warranty_mutation_gate()`:** These look similar but enforce domain-specific role frozensets. Merging into a generic gate would require passing role sets as params — this adds indirection without reducing complexity.

**Vessel cert vs crew cert handler paths:** Within `certificate_handlers.py`, vessel and crew paths share `_resolve_cert_domain()` but diverge after that (vessel has survey dates, crew has person_name). These branches look like duplication but represent genuinely different DB columns and business rules. Do not merge.

### 7C. Inline Types — Consolidate into Shared File

```typescript
// Currently defined inline in apps/web/src/app/certificates/page.tsx:19-32:
interface Certificate { id: string; domain?: 'vessel' | 'crew'; ... }

// Currently defined inline in apps/web/src/app/certificates/register/page.tsx:29-44:
interface CertRecord { id: string; certificate_name: string; status: string; ... }
```

Move both to `apps/web/src/types/certificate.ts` (new file). Import from there.  
Benefit: future pages (e.g., `/certificates/fleet`) can reuse without re-defining.

---

## 8. Cross-Domain Dependencies

### 8A. Handover Domain Directly Queries Cert Tables

**Documented in:** `docs/explanations/LENS_DOMAINS/certificates.md`
> "Handover exports can include cert status snapshots. The handover module pulls from `pms_vessel_certificates` and `pms_crew_certificates` directly via its own queries — it doesn't go through the cert handlers. Changes to cert schema need to be communicated to HANDOVER01."

**Impact:** Any column rename or table restructure in cert tables silently breaks handover export. There is no compile-time or test-time guard.

**What this means for changes:** If you rename `certificate_name` → `name`, or add a NOT NULL column, or change the `properties` JSONB schema — check `apps/api/services/handover_export_service.py` for direct cert table queries.

### 8B. `v_certificates_enriched` — Multiple Consumers

The UNION view is consumed by:
1. `rls_entity_validator.py:28` — ownership check
2. `useFilteredEntityList.ts` — cert list queries
3. `vessel_surface_routes.py` — register view data
4. Any spotlight search that spans cert domains

**Impact:** If the view is modified (new columns, column renames, removed cert_type values), all four consumers are affected. There is no migration file in the repo — it was applied via Supabase console.

### 8C. Notification Table — Platform-Wide Gap

`pms_notifications` is written by cert handlers (`_notify_cert_stakeholders()`) but has no confirmed frontend consumer as of 2026-04-19. The bell component exists and fetches from the API, but:
- The API endpoint for notifications may not be wired to the bell
- This is a platform-wide gap (Bug L), not cert-specific

**What not to break:** Do not remove the `pms_notifications` inserts in certificate_handlers.py. When the bell consumer is wired, the data needs to already be there.

### 8D. `projection.yaml` Defines Cert Search Scope

`apps/api/config/projection.yaml` defines which fields are indexed for spotlight search:
- Quick filters: `certificate_type`, `days_until_expiry`
- Both `certificates` and `crew_certificates` entity types included

Any new cert field that should be searchable needs to be added here.

---

## 9. Where to Enter the Repo for Any Change

> Use this as your navigation guide. One scenario = one entry point.

### "The cert list shows wrong data / missing certs / wrong status"
→ `useFilteredEntityList.ts` (query) + `v_certificates_enriched` (view) + `FilteredEntityList.tsx` (display)

### "The cert lens detail shows wrong data (name, dates, attachments, notes)"
→ `entity_routes.py:99` — `get_certificate_entity()` — assembles the full lens response

### "An action button is missing from / incorrectly in the dropdown"
→ `certificate_handlers.py` — `_get_certificate_actions()` — drives available_actions list  
→ `CertificateContent.tsx:240` — client-side filter (excludes create/assign/supersede)

### "An action is failing with 400 / 403 / 422"
→ `registry.py` — check allowed_roles and required_fields for that action_id  
→ `router.py` — validate_required_fields, validate_role_permission  
→ `certificate_handlers.py` — `_cert_mutation_gate()` — domain-specific role narrowing

### "An action is succeeding but nothing is happening in the DB"
→ `internal_dispatcher.py:INTERNAL_HANDLERS` — is the action_id registered?  
→ `certificate_handlers.py` — find the adapter function — is it calling the right handler?

### "The signature popup shows PIN instead of name-attestation (or vice versa)"
→ **Short term:** `CertificateContent.tsx:140–141` (the hardcoded downgrade)  
→ **Correct fix:** `registry.py` — add `signature_level: 2` to the cert action definition + remove the CertificateContent override

### "The renew flow is broken (upload → no renew popup)"
→ `CertificateContent.tsx:349,473–489` — `pendingRenew` state and the `onClose` trigger

### "Audit trail is empty after an action"
→ `certificate_handlers.py` — find the `try: db.table("pms_audit_log").insert(...) except Exception: pass` block for that action. The insert is failing silently.

### "Stakeholders aren't getting notifications"
→ `certificate_handlers.py:1642–1672` — `_notify_cert_stakeholders()` — check recipient query + notification insert  
→ Bell frontend: `Sidebar.tsx` bell component — confirm it's polling/fetching from the right endpoint

### "Cert creation has wrong fields / missing fields in the form"
→ `registry.py` — `field_metadata` for `create_vessel_certificate` / `create_crew_certificate`  
→ `mapActionFields.ts` — how `field_schema` is converted to form fields

### "The cert list sort options are wrong"
→ `FilteredEntityList.tsx:389–391` — the sort `<select>` options

### "Crew cert actions 404"
→ `rls_entity_validator.py:28` — `"certificate_id": "v_certificates_enriched"` — if this points to `pms_vessel_certificates`, crew certs will 404

### "Feature flag: enable/disable certificate functionality"
→ `apps/api/config/env.py` — `FEATURE_CERTIFICATES` (backend) + `UI_CERTIFICATES` (frontend display)  
→ **Naming issue:** Both are grouped under `FaultLensSettings` — confusing. Should be `CertificateSettings`.

### "Add a new cert action end-to-end"
1. `certificate_handlers.py` — write the handler function
2. `registry.py` — add `ActionDefinition` entry
3. `internal_dispatcher.py` — add wrapper to `INTERNAL_HANDLERS`
4. `certificate_handlers.py:_get_certificate_actions()` — add to available actions
5. `rls_entity_validator.py` — if action uses a new entity ID field, register it
6. `ledger_metadata.py` — add event_type mapping
7. `CertificateContent.tsx` — add to dropdown filter exclusion if needed
8. `apps/web/src/types/actions.ts:ACTION_DISPLAY` — add icon + cluster

### "Add a column to pms_vessel_certificates or pms_crew_certificates"
1. Apply migration via Supabase SQL editor (no committed migration file — project convention)
2. Update `certificate_handlers.py` — add field to select, insert, update queries
3. Update `entity_routes.py:get_certificate_entity()` — add to response shape
4. Update `v_certificates_enriched` view — re-run via Supabase SQL editor
5. Update `CertificateContent.tsx` — add to display sections
6. **Check `handover_export_service.py`** — direct cert table queries may need updating
7. Update `projection.yaml` if the new field should be searchable

### "Run the automated test suite"
```bash
# Playwright E2E runner (17 scenarios, targets production)
python3 tests/e2e/certificate_runner.py

# Python unit tests (handler-level, uses Supabase directly)
python3 apps/api/tests/cert_binary_tests.py

# TypeScript Playwright shards (run from apps/web/)
npx playwright test e2e/shard-53-certificate-e2e/
```

---

## Known Remaining Gaps (Not Defects — Logged for Awareness)

| Gap | Severity | Note |
|-----|----------|------|
| CI workflow references missing test file | HIGH | `.github/workflows/staging-certificates-acceptance.yml:44` — will always fail |
| SigL2 hardcoded in frontend | MEDIUM | `CertificateContent.tsx:140-141` — should move to backend registry |
| Notification bell has no frontend consumer | MEDIUM | Platform-wide gap (Bug L). Data is being written to `pms_notifications`. |
| `test_200_returns_correct_shape` broken mock | LOW | `test_entity_endpoints.py` — pre-existing, not a regression |
| Phase 4 shim redundant | LOW | `certificate_phase4_handler.py` — migration artifact |
| `certificate_routes.py` status unclear | LOW | Feature-gated, may be dead code |
| `as any` casts in CertificateContent.tsx | LOW | 6 instances — type safety gaps |
| Audit inserts fire-and-forget | MEDIUM | 8 silent `except Exception: pass` blocks |
| Missing ACTION_DISPLAY entries | LOW | Other cert actions use generic icon |
| Inline Certificate types in page files | LOW | Should be shared in `types/certificate.ts` |
| `FEATURE_CERTIFICATES` grouped under FaultLensSettings | LOW | Naming confusion in env.py |
| List counter clamp (shows 131 vs actual 440+) | LOW | Bug I — pagination artifact, not cert-specific |
