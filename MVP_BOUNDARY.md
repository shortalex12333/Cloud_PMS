# MVP Boundary - What's IN and What's NOT

**LOCKED FOR MVP - Any changes require explicit approval**

This document defines the hard line between MVP scope and future work.
Clear boundaries prevent scope creep and set correct expectations.

---

## ✅ IN MVP

### Email Integration
- [x] OAuth connection to Microsoft 365
- [x] Sync inbox and sent (last 30 days)
- [x] Display email list with metadata
- [x] View email content (cached body)
- [x] Basic text search
- [x] Semantic/vector search (when available)
- [x] Manual email-to-object linking
- [x] Suggested links with confidence scores
- [x] Undo link within 30 seconds
- [x] Graceful degradation when services fail

### PMS Features
- [x] Work order CRUD
- [x] Fault reporting
- [x] Equipment hierarchy
- [x] Checklists and tasks
- [x] Handover notes
- [x] Document attachments (upload/view)

### Single Surface UX
- [x] `/app` route as sole entry point
- [x] Spotlight search (Cmd+K)
- [x] Email panel (left slide)
- [x] Context panel (right slide)
- [x] State machine navigation (no URL changes for panels)

### Security
- [x] Row-level security on all tables
- [x] OAuth 2.0 token management
- [x] Yacht-level data isolation
- [x] Audit logging for link actions

### Cold Start / Onboarding
- [x] Progress indicators during first sync
- [x] Empty state explanations
- [x] First-link milestone celebration
- [x] "Learning" indicators

---

## ❌ NOT IN MVP

### Email Features We Are NOT Building
- ❌ Reply/compose/forward emails
- ❌ Delete emails
- ❌ Archive emails
- ❌ Email folder navigation
- ❌ Drafts
- ❌ Email notifications/alerts
- ❌ Email rules/filtering
- ❌ Attachment preview (link to Outlook only)
- ❌ Calendar integration
- ❌ Multi-account email

### Linking Features We Are NOT Building
- ❌ Auto-link without confirmation (even 100% confidence)
- ❌ Bulk link operations
- ❌ Link to multiple objects at once
- ❌ ML training on user corrections (logged only)
- ❌ Per-yacht threshold customization

### PMS Features Deferred
- ❌ Scheduled maintenance automation
- ❌ Parts inventory management
- ❌ Vendor portal
- ❌ Budget/cost tracking
- ❌ Compliance certificates management
- ❌ ISM integration
- ❌ Class survey integration

### UX Features Deferred
- ❌ Offline mode (full)
- ❌ Mobile app (responsive web only)
- ❌ Push notifications
- ❌ Dark mode
- ❌ Custom dashboard widgets
- ❌ Keyboard shortcut customization
- ❌ Multi-language support

### Analytics Deferred
- ❌ Usage analytics dashboard
- ❌ Email volume reports
- ❌ Link accuracy metrics
- ❌ Performance dashboards

### Admin Features Deferred
- ❌ Multi-yacht management console
- ❌ Fleet-wide analytics
- ❌ White-label branding
- ❌ SSO (SAML/OIDC)
- ❌ Admin audit logs

---

## ⚠️ EXPLICIT BOUNDARIES

### Email is Read-Only
The email integration is a **sensor**, not an email client. Users cannot:
- Send emails
- Modify emails
- Delete emails
- Move emails between folders

**Why:** Full email management is not our product. We surface context.

### Links Require Human Confirmation
Even 100% confidence suggestions require user confirmation:
- Deterministic matches (WO-1234 in subject) → one-click confirm
- High confidence → one-click confirm
- Medium confidence → explicit confirm dialog
- Low confidence → search and select

**Why:** Wrong auto-links destroy trust permanently.

### No Offline Functionality
The system requires network connectivity. In offline state:
- Show cached metadata only
- Disable all write operations
- Show clear offline indicator

**Why:** Satellite-first design means graceful degradation, not offline-first.

### Single Yacht Context
Each session operates in single-yacht context:
- No cross-yacht data access
- No fleet-level views
- No multi-yacht search

**Why:** RLS isolation is foundational. Multi-yacht is future work.

### 30-Day Email Window
We sync only:
- Last 30 days of Inbox
- Last 30 days of Sent

**Why:** Prevents unbounded storage growth. Older emails stay in Outlook.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01 | No auto-link | Trust > convenience |
| 2026-01 | 30-day window | Storage constraints |
| 2026-01 | No reply/compose | Not our product |
| 2026-01 | Single surface only | Reduce confusion |
| 2026-01 | No offline writes | Data integrity |

---

## When to Revisit

These boundaries should be revisited when:
1. First 10 yachts have used the system for 30+ days
2. We have correction data showing suggestion accuracy
3. User feedback explicitly requests a NOT IN MVP feature
4. Technical constraints change (e.g., offline-capable infra)

---

## Scope Creep Defense

If someone asks for a NOT IN MVP feature, the response is:

> "That's on our roadmap but not in the MVP scope. We're focused on
> getting the core email-linking experience right before adding more.
> Would you like to add it to the feature request list?"

Do not negotiate MVP boundaries mid-build.
