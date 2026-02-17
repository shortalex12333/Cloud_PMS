# Requirements: CelesteOS v1.0 — Lens Completion

**Defined:** 2026-02-17
**Core Value:** Crew can complete maintenance tasks faster with fewer clicks than any existing PMS, with full audit trail.

---

## v1 Requirements

Each lens follows the 9-step testing protocol from `/Users/celeste7/Desktop/rules.md`.

### Design System (DS) — BLOCKING

- [ ] **DS-01**: tokens.css implemented with dark + light CSS custom properties
- [ ] **DS-02**: tailwind.config.js extended with semantic token mappings
- [ ] **DS-03**: Base components built (StatusPill, SectionContainer, GhostButton, PrimaryButton, EntityLink, Toast)
- [ ] **DS-04**: VitalSignsRow component built and rendering
- [ ] **DS-05**: All "email integration is off" instances removed

### Receiving Lens (RECV)

- [ ] **RECV-01**: PR #332 merged and deployed
- [ ] **RECV-02**: Crew test user provisioned in Supabase auth
- [ ] **RECV-03**: All 10 E2E tests passing
- [ ] **RECV-04**: Ledger triggers verified for receiving actions

### Parts/Inventory Lens (PART)

- [ ] **PART-01**: DB schema verified (RLS, FK, constraints)
- [ ] **PART-02**: Backend handler tests passing (all roles)
- [ ] **PART-03**: Frontend renders all required values
- [ ] **PART-04**: E2E tests for CRUD operations
- [ ] **PART-05**: Ledger triggers verified

### Equipment Lens (EQUIP)

- [ ] **EQUIP-01**: DB schema verified (RLS, FK, constraints)
- [ ] **EQUIP-02**: Backend handler tests passing (all roles)
- [ ] **EQUIP-03**: Frontend renders all required values
- [ ] **EQUIP-04**: E2E tests for CRUD operations
- [ ] **EQUIP-05**: Ledger triggers verified

### Fault Lens (FAULT)

- [ ] **FAULT-01**: DB schema verified (RLS, FK, constraints)
- [ ] **FAULT-02**: Backend handler tests passing (all roles)
- [ ] **FAULT-03**: Frontend renders all required values
- [ ] **FAULT-04**: E2E tests for CRUD operations
- [ ] **FAULT-05**: Ledger triggers verified

### Work Order Lens (WO)

- [ ] **WO-01**: DB schema verified (RLS, FK, constraints)
- [ ] **WO-02**: Backend handler tests passing (all roles)
- [x] **WO-03**: Frontend gaps fixed (6 actions missing)
- [ ] **WO-04**: E2E tests for CRUD operations
- [ ] **WO-05**: Ledger triggers verified

### Certificate Lens (CERT)

- [ ] **CERT-01**: DB schema verified (RLS, FK, constraints)
- [ ] **CERT-02**: Backend handler tests passing (all roles)
- [x] **CERT-03**: Frontend renders all required values
- [x] **CERT-04**: E2E tests for CRUD operations
- [ ] **CERT-05**: Ledger triggers verified

### Handover Lens (HAND)

- [ ] **HAND-01**: DB schema verified (RLS, FK, constraints)
- [x] **HAND-02**: Backend handler tests passing (all roles)
- [x] **HAND-03**: Frontend renders all required values
- [ ] **HAND-04**: E2E tests for CRUD operations
- [ ] **HAND-05**: Ledger triggers verified

### Hours of Rest Lens (HOR)

- [ ] **HOR-01**: DB schema verified (RLS, FK, constraints)
- [ ] **HOR-02**: Backend handler tests passing (all roles)
- [ ] **HOR-03**: Frontend renders all required values
- [ ] **HOR-04**: E2E tests for CRUD operations
- [ ] **HOR-05**: Ledger triggers verified

### Warranty Lens (WARR)

- [ ] **WARR-01**: DB schema verified (RLS, FK, constraints)
- [ ] **WARR-02**: Backend handler tests passing (all roles)
- [x] **WARR-03**: Frontend renders all required values
- [x] **WARR-04**: E2E tests for CRUD operations
- [x] **WARR-05**: Ledger triggers verified

### Shopping List Lens (SHOP)

- [ ] **SHOP-01**: DB schema verified (RLS, FK, constraints)
- [ ] **SHOP-02**: Backend handler tests passing (all roles)
- [ ] **SHOP-03**: Frontend renders all required values
- [ ] **SHOP-04**: E2E tests for CRUD operations
- [x] **SHOP-05**: Ledger triggers verified

### Email Lens (EMAIL)

- [x] **EMAIL-01**: Handler file created (email_handlers.py)
- [ ] **EMAIL-02**: 5 actions implemented per registry
- [ ] **EMAIL-03**: DB schema verified (RLS, FK, constraints)
- [ ] **EMAIL-04**: Backend handler tests passing (all roles)
- [ ] **EMAIL-05**: E2E tests for email operations
- [ ] **EMAIL-06**: Ledger triggers verified

### Cross-Lens Cleanup (CLEAN)

- [x] **CLEAN-01**: Remove "email integration is off" from all lenses
- [ ] **CLEAN-02**: All lenses open to full screen (not side-view-card)
- [ ] **CLEAN-03**: Action buttons adjacent to their sections
- [x] **CLEAN-04**: Signature confirmation where required

---

## v2 Requirements (Deferred)

### Navigation Enhancement
- **NAV-01**: Show Related full implementation
- **NAV-02**: Back/forward navigation stack
- **NAV-03**: Cross-lens embedded links

### Search Enhancement
- **SEARCH-01**: Graph RAG semantic search
- **SEARCH-02**: Vector embeddings for entities

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Native mobile app | Web-first, mobile v2 |
| Offline mode | Complexity, v2+ |
| Multi-language | English first |
| Custom themes | Default theme only |
| Voice notes | v2 feature |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RECV-01 | 1 | Pending |
| RECV-02 | 1 | Pending |
| RECV-03 | 1 | Pending |
| RECV-04 | 1 | Pending |
| PART-01 | 2 | Pending |
| PART-02 | 2 | Pending |
| PART-03 | 2 | Pending |
| PART-04 | 2 | Pending |
| PART-05 | 2 | Pending |
| EQUIP-01 | 3 | Pending |
| EQUIP-02 | 3 | Pending |
| EQUIP-03 | 3 | Pending |
| EQUIP-04 | 3 | Pending |
| EQUIP-05 | 3 | Pending |
| FAULT-01 | 4 | Pending |
| FAULT-02 | 4 | Pending |
| FAULT-03 | 4 | Pending |
| FAULT-04 | 4 | Pending |
| FAULT-05 | 4 | Pending |
| WO-01 | 5 | Pending |
| WO-02 | 5 | Pending |
| WO-03 | 5 | Complete |
| WO-04 | 5 | Pending |
| WO-05 | 5 | Pending |
| CERT-01 | 6 | Pending |
| CERT-02 | 6 | Pending |
| CERT-03 | 6 | Complete |
| CERT-04 | 6 | Complete |
| CERT-05 | 6 | Pending |
| HAND-01 | 7 | Pending |
| HAND-02 | 7 | Complete |
| HAND-03 | 7 | Complete |
| HAND-04 | 7 | Pending |
| HAND-05 | 7 | Pending |
| HOR-01 | 8 | Pending |
| HOR-02 | 8 | Pending |
| HOR-03 | 8 | Pending |
| HOR-04 | 8 | Pending |
| HOR-05 | 8 | Pending |
| WARR-01 | 9 | Pending |
| WARR-02 | 9 | Pending |
| WARR-03 | 9 | Complete |
| WARR-04 | 9 | Complete |
| WARR-05 | 9 | Complete |
| SHOP-01 | 10 | Pending |
| SHOP-02 | 10 | Pending |
| SHOP-03 | 10 | Pending |
| SHOP-04 | 10 | Pending |
| SHOP-05 | 10 | Complete |
| EMAIL-01 | 11 | Complete |
| EMAIL-02 | 11 | Pending |
| EMAIL-03 | 11 | Pending |
| EMAIL-04 | 11 | Pending |
| EMAIL-05 | 11 | Pending |
| EMAIL-06 | 11 | Pending |
| CLEAN-01 | 12 | Complete |
| CLEAN-02 | 12 | Pending |
| CLEAN-03 | 12 | Pending |
| CLEAN-04 | 12 | Complete |

**Coverage:**
- v1 requirements: 60 total
- Mapped to phases: 60
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-17*
*Last updated: 2026-02-17 after initial definition*
