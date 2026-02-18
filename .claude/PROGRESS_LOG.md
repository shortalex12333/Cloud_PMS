# CelesteOS Progress Log

**Scope**: Frontend UX Engineering — 1-URL Single Surface Architecture
**Status**: REMEDIATION COMPLETE

---

## Architecture: 1-URL Philosophy

Per `rules.md`:
> "We operate on a 1-url philosophy. Any fragmented frontend URLS are strictly forbidden."

**Single URL**: `app.celeste7.ai` (renders at `/`)
**All entities**: Render inside ContextPanel via LensRenderer
**NO separate routes**: No `/work-orders/[id]`, `/faults/[id]`, etc.

---

## FE-REMEDIATION (2026-02-17)

### Critical Fix: Deleted Fragmented Routes

**BEFORE** (violation of rules.md):
- 11 page routes at `/work-orders/[id]`, `/faults/[id]`, `/equipment/[id]`, etc.
- Old `Lens.tsx` files with hardcoded URL navigation
- `useDocumentNavigation` using `router.push` to deleted routes

**AFTER** (compliant):
- All 11 fragmented routes **DELETED**
- 11 `LensContent.tsx` components render inside ContextPanel
- LensRenderer maps entity types to LensContent components
- `useDocumentNavigation` uses `showContext()` from SurfaceContext
- Shared `types.ts` for lens data types

### Files Deleted

```
apps/web/src/app/certificates/[id]/page.tsx
apps/web/src/app/documents/[id]/page.tsx
apps/web/src/app/equipment/[id]/page.tsx
apps/web/src/app/faults/[id]/page.tsx
apps/web/src/app/handover/[id]/page.tsx
apps/web/src/app/hours-of-rest/[id]/page.tsx
apps/web/src/app/parts/[id]/page.tsx
apps/web/src/app/receiving/[id]/page.tsx
apps/web/src/app/shopping-list/[id]/page.tsx
apps/web/src/app/warranty/[id]/page.tsx
apps/web/src/app/work-orders/[id]/page.tsx

apps/web/src/components/lens/CertificateLens.tsx
apps/web/src/components/lens/DocumentLens.tsx
apps/web/src/components/lens/EquipmentLens.tsx
apps/web/src/components/lens/FaultLens.tsx
apps/web/src/components/lens/HandoverLens.tsx
apps/web/src/components/lens/HoursOfRestLens.tsx
apps/web/src/components/lens/PartsLens.tsx
apps/web/src/components/lens/ReceivingLens.tsx
apps/web/src/components/lens/ShoppingListLens.tsx
apps/web/src/components/lens/WarrantyLens.tsx
apps/web/src/components/lens/WorkOrderLens.tsx
```

### Files Created/Updated

```
apps/web/src/components/lens/types.ts           # Shared lens data types
apps/web/src/hooks/useDocumentNavigation.ts     # Uses showContext() now
apps/web/src/app/email/inbox/page.tsx           # Fixed hardcoded colors
```

---

## Current Architecture

### Routing

| URL | Purpose |
|-----|---------|
| `/` | Root surface - redirects to `/app` or handles auth |
| `/app` | Single surface with SpotlightSearch + ContextPanel |
| `/login` | Authentication |
| `/open?t=<token>` | Handover link resolution (redirects to `/app`) |
| `/email/inbox` | Legacy redirect to `/app?openEmail=true` |

### LensContent Components (ContextPanel Rendering)

| Component | Entity Type | Located At |
|-----------|-------------|------------|
| WorkOrderLensContent | `work_order` | `components/lens/` |
| FaultLensContent | `fault` | `components/lens/` |
| EquipmentLensContent | `equipment` | `components/lens/` |
| PartsLensContent | `part`, `inventory` | `components/lens/` |
| CertificateLensContent | `certificate` | `components/lens/` |
| ReceivingLensContent | `receiving` | `components/lens/` |
| HandoverLensContent | `handover` | `components/lens/` |
| HoursOfRestLensContent | `hours_of_rest` | `components/lens/` |
| WarrantyLensContent | `warranty` | `components/lens/` |
| ShoppingListLensContent | `shopping_list` | `components/lens/` |
| DocumentLensContent | `document` | `components/lens/` |

### Navigation Flow

```
User clicks entity -> showContext(type, id) ->
  SurfaceContext updates -> ContextPanel renders ->
  LensRenderer maps to LensContent -> Entity displayed
```

---

## Build Status

```
TypeScript: 0 errors
Routes: /app, /login, /open (single surface architecture)
Fragmented routes: DELETED
```

---

## Known Issues (Non-Blocking)

1. **282 hardcoded hex colors** in 19 files - should use design tokens
2. **35 inline style={{}}** blocks - should use Tailwind classes
3. **6 !important** declarations in CSS
4. **7 z-index** inconsistencies (mix of hardcoded + CSS variables)

---

*Last Updated: 2026-02-17*
*FE-REMEDIATION: 1-URL architecture enforced*
