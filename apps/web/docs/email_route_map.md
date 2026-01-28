# Email Route Map

> Canonical reference for all email-related routes, components, hooks, and backend endpoints.
> Updated: 2026-01-28

## Routes

| Route | Component | Purpose | Data Sources | Status |
|-------|-----------|---------|--------------|--------|
| `/email/inbox` | `EmailSurface` | Three-column Outlook-style email interface | `GET /email/inbox`, `GET /email/thread/:id`, `GET /email/message/:id/render`, `GET /email/search` | **Active (canonical)** |
| `/email/search` | _removed_ | Redirect to `/email/inbox` | - | **Deprecated** |
| `/app` | `SpotlightSearch` > `EmailInboxView` | Inline email list under spotlight | `GET /email/inbox` | Active (no body render) |

## API Proxy Routes (Next.js)

| Route | Method | Purpose | Backend Target | Auth | Runtime |
|-------|--------|---------|---------------|------|---------|
| `/api/email/search` | POST | Hybrid semantic search | Python `/email/search` (proxied) | Bearer JWT | nodejs, force-dynamic |
| `/api/integrations/outlook/status` | GET | Connection status | `pipeline-core/auth/outlook/status` | Bearer JWT | nodejs, force-dynamic, no-store |
| `/api/integrations/outlook/auth-url` | GET | OAuth URL (READ) | Local (oauth-utils) | Bearer JWT | nodejs, force-dynamic, no-store |
| `/api/integrations/outlook/callback` | GET | OAuth callback (READ) | `pipeline-core/auth/outlook/exchange` | None (OAuth flow) | nodejs, force-dynamic |
| `/api/integrations/outlook/disconnect` | POST | Revoke tokens | Supabase direct | Bearer JWT | nodejs |
| `/api/integrations/outlook/write/auth-url` | GET | OAuth URL (WRITE) | Local (oauth-utils) | Bearer JWT | nodejs, force-dynamic |
| `/api/integrations/outlook/write/callback` | GET | OAuth callback (WRITE) | `pipeline-core/auth/outlook/exchange` | None (OAuth flow) | nodejs, force-dynamic |

## Backend Endpoints (Python/Render)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/email/inbox` | GET | Paginated thread list with filters |
| `/email/search` | GET | Hybrid semantic + entity search with operators |
| `/email/thread/{thread_id}` | GET | Thread with all messages |
| `/email/message/{provider_message_id}/render` | GET | Fetch body from Graph API (no storage) |
| `/email/message/{message_id}/attachments` | GET | List attachment metadata |
| `/email/message/{provider_message_id}/attachments/{id}/download` | GET | Stream download |
| `/email/focus/{message_id}` | GET | Single message with context |
| `/email/related` | GET | Threads linked to an object |
| `/email/search-objects` | GET | Search linkable objects |
| `/email/link/add` | POST | Create link |
| `/email/link/accept` | POST | Accept suggested link |
| `/email/link/change` | POST | Change link target |
| `/email/link/remove` | POST | Remove link |
| `/email/worker/status` | GET | Backfill status |
| `/email/worker/backfill` | POST | Trigger import |
| `/auth/outlook/status` | GET | OAuth connection status |
| `/auth/outlook/exchange` | POST | OAuth code exchange |

## Components (Canonical)

| Component | File | Purpose | Owner |
|-----------|------|---------|-------|
| `EmailSurface` | `components/email/EmailSurface.tsx` | Three-column layout (threads / body / attachments) | **Canonical email UI** |
| `EmailInboxView` | `components/email/EmailInboxView.tsx` | Simple thread list for SpotlightSearch inline | Spotlight integration |
| `RelatedEmailsPanel` | `components/email/RelatedEmailsPanel.tsx` | Linked emails for context panel | Context panel |
| `LinkEmailModal` | `components/email/LinkEmailModal.tsx` | Modal for linking emails to objects | Link management |
| `EmailLinkActions` | `components/email/EmailLinkActions.tsx` | Accept/Change/Unlink buttons | Link management |
| `EmailThreadViewer` | `components/email/EmailThreadViewer.tsx` | Thread message list with body iframe | Thread display |

## Hooks

| Hook | File | Purpose |
|------|------|---------|
| `useEmailData` | `hooks/useEmailData.ts` | All email React Query hooks + auth fetch |
| `useEmailDataDebug` | `hooks/useEmailDataDebug.ts` | Debug fault tracking (development only) |

## Deprecated / Legacy

| File | Reason | Replacement |
|------|--------|-------------|
| `_legacy/EmailSearchView.tsx` | Replaced by EmailSurface | `EmailSurface.tsx` |
| `/email/search/page.tsx` | Separate search page unnecessary | `/email/inbox` handles search |

## Non-Negotiables

- `encodeURIComponent` on all provider_message_id and provider_attachment_id in URLs
- Bearer JWT only (no cookie auth)
- No body storage; render/download stream only
- Watcher.user_id must match token.user_id
