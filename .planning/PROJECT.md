# CelesteOS — Cloud PMS

> **Vision**: Intent-first maritime vessel management platform with AI-powered lenses.

---

## Scope: Frontend UX Engineering

**Role**: Frontend UX Engineer only. No backend operations.

**Focus Areas**:
- UI/UX design and implementation
- Component development (React, TypeScript)
- Styling (Tailwind CSS, CSS custom properties)
- User interaction patterns
- Accessibility
- Visual consistency
- Responsive design

---

## Technical Stack (Frontend Only)

| Layer | Technology |
|-------|------------|
| Framework | Next.js 14, React |
| Language | TypeScript |
| Styling | Tailwind CSS, CSS custom properties |
| Testing | Playwright (E2E), visual regression |
| Deployment | Vercel |

---

## Architecture Principles (Frontend)

1. **Single-URL Philosophy** — No fragmented navigation, everything embedded
2. **Intent-First** — Users express intent, system routes to action
3. **Tokenized UI** — All styling via CSS custom properties
4. **Component Isolation** — Reusable, testable components
5. **Accessibility First** — WCAG compliance

---

## Completed Work

- Search Bar UX (ChatGPT parity) — PRs #327, #328, #330
  - Shadow only, no border
  - Removed Mic/Search icons
  - Removed category buttons
  - Tokenized shadow via `--celeste-spotlight-shadow`

---

## References

- `/docs/SOURCE_OF_TRUTH.md` — Canonical state
- `/docs/UI_LOCKS.md` — UI invariants
- `/.claude/PROGRESS_LOG.md` — Live tracking

---
*Scope: Frontend UX Engineering Only*
*Last updated: 2026-02-17*
