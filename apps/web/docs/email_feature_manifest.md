# Email Feature Manifest

> Feature coverage matrix for email functionality.
> Updated: 2026-01-28

## Feature Coverage Matrix

| Feature | Component | Backend Endpoint | Test Coverage | Status |
|---------|-----------|------------------|---------------|--------|
| Thread list | `EmailSurface` | `GET /email/inbox` | E2E: `email-ui-render.spec.ts`, `email-api-smoke.spec.ts` | **Production** |
| Thread detail | `EmailSurface` | `GET /email/thread/:id` | E2E: `email-api-smoke.spec.ts` | **Production** |
| Body render (fetch-on-click) | `EmailSurface` | `GET /email/message/:id/render` | E2E: `email-api-smoke.spec.ts` | **Production** |
| Attachment list | `EmailSurface` | `GET /email/message/:id/attachments` | E2E: `email-api-smoke.spec.ts` | **Production** |
| Attachment download | `EmailSurface` | `GET /email/message/:id/attachments/:id/download` | E2E: `email-api-smoke.spec.ts` | **Production** |
| Hybrid search | `SpotlightSearch` | `POST /api/email/search` → `GET /email/search` | E2E: `email-api-smoke.spec.ts` | **Production** |
| Object linking | `LinkEmailModal` | `POST /email/link/add` | Manual only | **Production** |
| Link accept | `EmailLinkActions` | `POST /email/link/accept` | Manual only | **Production** |
| Link change | `EmailLinkActions` | `POST /email/link/change` | Manual only | **Production** |
| Link remove | `EmailLinkActions` | `POST /email/link/remove` | Manual only | **Production** |
| Related emails | `RelatedEmailsPanel` | `GET /email/related` | Manual only | **Production** |
| OAuth connect (READ) | Settings | `GET /api/integrations/outlook/auth-url` | Manual only | **Production** |
| OAuth status | Settings | `GET /api/integrations/outlook/status` | Manual only | **Production** |
| OAuth disconnect | Settings | `POST /api/integrations/outlook/disconnect` | Manual only | **Production** |

## Auth Flow

```
User Request
    │
    ▼
SpotlightSearch / EmailSurface
    │
    ├─► getAuthHeaders() (centralized from authHelpers.ts)
    │      │
    │      ├─► getValidJWT() - auto-refresh if expiring
    │      │
    │      └─► Bearer token header
    │
    ▼
authFetch() (401 retry wrapper)
    │
    ▼
Python Backend (/email/*)
    │
    └─► JWT verified, yacht_id from user lookup
```

## Search Flow

```
User types in SpotlightSearch (Email Scope active)
    │
    ▼
searchEmail() in SpotlightSearch.tsx
    │
    ├─► POST /api/email/search (Next.js proxy)
    │      │
    │      └─► GET /email/search?q=... (Python backend)
    │              │
    │              ├─► Query parsing (operators)
    │              ├─► Embedding generation (cached)
    │              └─► Hybrid search RPC
    │
    ▼
Results displayed in SpotlightSearch
```

## Hybrid Search Architecture

**Canonical embedding column: `email_messages.meta_embedding` (VECTOR(1536))**

- Migration 26 (`search_email_hybrid`) uses `meta_embedding`
- Backfill worker writes to `meta_embedding`
- Legacy `embedding` column is deprecated; do not use for new code

Scoring weights:
- Vector similarity: 60%
- Entity keyword match: 25%
- Recency/affinity/linkage signals: 15% (M3)

## Error Map

| HTTP Status | Code | Meaning | UI Response |
|-------------|------|---------|-------------|
| 401 | `missing_bearer` | No Authorization header | Redirect to login |
| 401 | `invalid_token` | Token expired/invalid | Refresh + retry once |
| 401 | `token_invalid` | Supabase getUser failed | Redirect to login |
| 413 | - | Attachment too large | Toast: "File too large" |
| 415 | - | Attachment type disallowed | Toast: "File type not allowed" |
| 500 | `internal_error` | Server error | Toast: "Something went wrong" |

## Security Non-Negotiables

| Rule | Implementation |
|------|---------------|
| Bearer JWT only | `authHelpers.ts:getAuthHeaders()` |
| No body storage | `/render` endpoint fetches from Graph API |
| `encodeURIComponent` on provider IDs | `useEmailData.ts:fetchMessageContent()`, `downloadAndSaveAttachment()` |
| User-watcher ownership check | Backend middleware |
| 401 auto-retry | `useEmailData.ts:authFetch()` |
| External images blocked | `EmailSurface.tsx:sanitizeHtml()` - replaces src with data-blocked-src |
| Cache-Control: no-store | All auth-required API routes |

## Component Ownership

| Component | Responsibility | File |
|-----------|---------------|------|
| **EmailSurface** | Canonical three-column email UI | `components/email/EmailSurface.tsx` |
| **EmailInboxView** | Inline thread list for SpotlightSearch | `components/email/EmailInboxView.tsx` |
| **SpotlightSearch** | Email scope search toggle | `components/spotlight/SpotlightSearch.tsx` |
| **useEmailData** | All email React Query hooks | `hooks/useEmailData.ts` |
| **authHelpers** | Centralized JWT management | `lib/authHelpers.ts` |

## Test Coverage Summary

| Test Suite | Tests | Status |
|------------|-------|--------|
| `email-api-smoke.spec.ts` | 8 | **Passing** |
| `email-ui-render.spec.ts` | 4 | **Passing** |
| Backend unit tests | N/A | Backend repo |

## Deprecated Components

| File | Reason | Replacement |
|------|--------|-------------|
| `_legacy/EmailSearchView.tsx` | Renamed to EmailSurface | `EmailSurface.tsx` |
| `/email/search/page.tsx` | Redirects to `/email/inbox` | `/email/inbox` |

## Known Limitations

| Gap | Impact | Status |
|-----|--------|--------|
| ~~OpenAI unavailable returns 500~~ | ~~Search fails if OPENAI_API_KEY missing~~ | ✅ **Fixed** (commit `1807e99`) |
| Attachment download test skipped | No attachments in test account | Add fixture emails with attachments |
| cid: images require manual load | Inline images not auto-displayed | User intent required for privacy |

### Entity-Only Fallback (Implemented)

When embeddings are unavailable (OpenAI key missing or API failure), search degrades gracefully to entity keyword matching:

```python
# routes/email.py - search_emails handler (lines 550-552)
if not embedding:
    logger.warning("[email/search] No embedding available; degrading to entity-only search")
    embedding = [0.0] * 1536  # Neutral vector
    telemetry['embed_skipped'] = True  # Triggers threshold=0.0
```

When vector lane is disabled (`embed_skipped=True`):
- `p_similarity_threshold` is set to `0.0`
- Results driven by entity keywords (`p_entity_keywords`)
- Telemetry tracks degraded mode for monitoring

## Related Documentation

- [Route Map](./email_route_map.md) - All routes and endpoints
- [API Security](./API_SECURITY.md) - Auth patterns
- Backend: `apps/api/routes/email.py`
