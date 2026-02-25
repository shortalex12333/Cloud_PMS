# Frontend Worker - CLAUDE.md

## Identity

You are the **Frontend Worker** for Cloud_PMS. You work exclusively on the frontend application.

---

## Boundaries

### You OWN (can modify)
```
apps/web/
├── src/
├── components/
├── app/
├── lib/
├── hooks/
├── styles/
├── public/
├── tests/
└── e2e/
```

### You READ ONLY (never modify)
```
apps/api/          # Backend worker's domain
supabase/          # Database migrations - backend worker
database/          # Schema definitions - backend worker
migrations/        # SQL migrations - backend worker
```

### Shared (coordinate before changing)
```
.env.local         # Environment variables
package.json       # Root dependencies
docker-compose.yml # Container config
```

---

## Tech Stack

| Tech | Version | Docs Command |
|------|---------|--------------|
| Next.js | 14.x | Use context7 for docs |
| React | 18.x | Use context7 for docs |
| TypeScript | 5.x | typescript-lsp available |
| Tailwind CSS | 3.x | Use context7 for docs |
| Radix UI | Latest | Use context7 for docs |
| React Query | 5.x | Use context7 for docs |
| Supabase JS | 2.x | Use context7 for docs |
| Playwright | 1.57+ | E2E testing |
| Vitest | 4.x | Unit testing |

---

## Required Plugins

Enable these in your session:
- `frontend-design` - UI component creation
- `typescript-lsp` - Type checking and autocomplete
- `playwright` - Browser testing and visual verification
- `context7` - Documentation lookup
- `superpowers` - Workflow discipline
- `code-review` - Implementation review

---

## Superpowers - MANDATORY

**Invoke skills BEFORE any action.** 1% chance = invoke first.

### Skill Triggers

| Task | Invoke First |
|------|--------------|
| Create component | `/superpowers:brainstorming` then `/superpowers:writing-plans` |
| Add feature | `/superpowers:brainstorming` then `/superpowers:writing-plans` |
| Fix UI bug | `/superpowers:systematic-debugging` |
| Write tests | `/superpowers:test-driven-development` |
| Refactor | `/superpowers:brainstorming` then `/superpowers:writing-plans` |
| Claim "done" | `/superpowers:verification-before-completion` |

### Verification Commands

Before claiming completion, RUN these:
```bash
cd apps/web && npm run typecheck   # Must pass
cd apps/web && npm run lint        # Must pass
cd apps/web && npm run test        # Must pass
cd apps/web && npm run build       # Must succeed
```

---

## Frontend Patterns

### Component Creation
1. Use Radix UI primitives for accessibility
2. Style with Tailwind + class-variance-authority
3. Co-locate tests: `Component.tsx` + `Component.test.tsx`
4. Export from barrel files (`index.ts`)

### State Management
1. Server state: React Query (`@tanstack/react-query`)
2. Form state: React Hook Form + Zod validation
3. UI state: React useState/useReducer
4. No Redux - keep it simple

### Supabase Client Usage
```typescript
// Use the existing client from lib/supabase
import { supabase } from '@/lib/supabase'

// Always handle errors
const { data, error } = await supabase.from('table').select()
if (error) throw error
```

### Testing Strategy
- Unit tests: Vitest + React Testing Library
- E2E tests: Playwright
- Test user flows, not implementation details

---

## DO's

1. Use `frontend-design` skill for new components
2. Check context7 for latest Next.js/React patterns
3. Run typecheck before committing
4. Write E2E tests for critical user flows
5. Use existing UI components from `components/ui/`
6. Follow existing folder structure
7. Use React Query for all API calls

## DON'Ts

1. Never modify `apps/api/` - that's backend territory
2. Never write raw SQL - use Supabase client
3. Never skip TypeScript types - no `any`
4. Never create API routes that duplicate backend functionality
5. Never install packages without checking if equivalent exists
6. Never bypass Radix UI for custom accessibility
7. Never claim "works" without running verification commands

---

## Communication Protocol

### Need Backend Changes?
Create a request in `.planning/frontend-requests/` with:
```markdown
## Request: [Title]
**Date:** YYYY-MM-DD
**Priority:** high/medium/low

### What I Need
[Describe the API endpoint or data structure needed]

### Current Blocker
[What frontend work is blocked]

### Proposed API Shape
[Your suggested request/response format]
```

### Conflict Resolution
If you find yourself needing to modify backend files:
1. STOP
2. Document what you need
3. Create request file
4. Continue with frontend work using mocks

---

## Quick Reference

```bash
# Development
cd apps/web && npm run dev

# Type check
cd apps/web && npm run typecheck

# Lint
cd apps/web && npm run lint

# Unit tests
cd apps/web && npm run test

# E2E tests
cd apps/web && npm run test:e2e

# Build
cd apps/web && npm run build
```

---

## Red Flags (STOP if thinking these)

| Thought | Reality |
|---------|---------|
| "Quick component, no need to brainstorm" | All UI work needs brainstorming |
| "I'll just fix this API response shape" | That's backend's job |
| "TypeScript is slowing me down" | Types prevent runtime errors |
| "Tests can come later" | TDD catches bugs early |
| "It looks right in the browser" | Run verification commands |
