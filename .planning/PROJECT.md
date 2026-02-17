# CelesteOS — Cloud PMS

> **Vision**: Intent-first maritime vessel management platform with AI-powered lenses.

---

## What This Is

CelesteOS is a cloud-based Property Management System (PMS) for maritime yachts. It replaces traditional multi-page navigation with a single-URL, intent-first interface where crew can "do something" rather than "go somewhere." Database is truth, every action is auditable, immutable ledger for compliance.

## Core Value

**Crew can complete maintenance tasks faster with fewer clicks than any existing PMS, with full audit trail.**

---

## Current Milestone: v1.0 — Lens Completion

**Goal:** Complete all 16 entity lenses with backend handlers, frontend rendering, and E2E test coverage.

**Target features:**
- All lens handlers implemented (including missing Email lens)
- 9-step testing protocol passed per lens
- Full E2E coverage with role-based testing (crew, HOD, captain)
- Ledger triggers verified for audit trail
- Remove "email integration is off" legacy code

---

## Technical Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS |
| Backend | Python (FastAPI), Supabase Edge Functions |
| Database | PostgreSQL (Supabase), RLS policies |
| OCR | Tesseract (Docker service on port 8001) |
| Auth | Supabase Auth, JWT |
| Testing | Playwright (E2E), pytest (backend) |
| Deployment | Vercel (frontend), Docker (services) |

---

## Architecture Principles

1. **Single-URL Philosophy** — No fragmented navigation, everything embedded
2. **Intent-First** — Users express intent, system routes to action
3. **Yacht Isolation** — All queries filtered by yacht_id via RLS
4. **Service Role Bypass** — Backend uses service_role, action registry controls permissions
5. **Tokenized UI** — All styling via CSS custom properties
6. **Atomic Commits** — One task = one commit
7. **Ledger Everything** — Every action logged for audit trail

---

## Requirements

### Validated

- ✓ Spotlight Search (ChatGPT parity) — Search Bar Phase complete
- ✓ OCR Pipeline — Docker service working
- ✓ Multi-tenant RLS — Yacht isolation verified
- ✓ Document Lens — 98% test coverage (PRODUCTION)

### Active

See `.planning/REQUIREMENTS.md` for full list with REQ-IDs.

### Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile app | Web-first, mobile later |
| Show Related (full) | Future feature, architecture exists |
| Real-time chat | Not core to PMS value |
| Graph RAG search | V2 feature |

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Shadow-only search bar | ChatGPT parity spec | ✓ Good |
| All crew can create receiving | Draft mode workflow | ✓ Good |
| HOD+ for accept | Financial accountability | ✓ Good |
| Service role bypass | Backend needs full access for multi-tenant | ✓ Good |
| Confidence in payload | Schema simplicity | ✓ Good |
| 9-step test protocol | User requirement for quality | — Pending |

---

## References

- `/docs/SOURCE_OF_TRUTH.md` — Canonical state
- `/docs/UI_LOCKS.md` — UI invariants
- `/docs/DB_CONTRACT.md` — Schema, RLS, roles
- `/docs/TEST_ORDER.md` — Test sequence
- `/Users/celeste7/Desktop/rules.md` — Operating rules
- `/.planning/codebase/` — Architecture documentation

---
*Last updated: 2026-02-17 after M1 milestone initialization*
