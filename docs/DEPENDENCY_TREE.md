# CelesteOS Frontend Dependency Tree

**Generated:** Planning Phase
**Purpose:** Reference for Brand & UX overhaul
**Philosophy:** "Traditional software = users adapt. CelesteOS = UX adapts to users."

---

## 1. FOUNDATION LAYER (Tokens & Config)

### Design Token System
```
src/styles/
├── tokens/
│   ├── index.ts          # Barrel export - all tokens
│   ├── colors.ts         # Color palette (whites, blacks, accent, restricted)
│   ├── typography.ts     # Font families, sizes, weights, text styles
│   ├── spacing.ts        # 4px grid, component spacing, layout
│   ├── shadows.ts        # Elevation levels, blur, glass effects
│   ├── motion.ts         # Duration, easing, transitions
│   └── forbidden.ts      # Banned elements, phrases, patterns
├── design-system.ts      # Higher-level design utilities
├── design-tokens.ts      # Legacy/compat tokens
└── globals.css           # CSS variables, base styles, animations
```

### Tailwind Configuration
```
tailwind.config.ts        # CRITICAL: Must lock down all allowed values
```

### Key Token Files (Already Exist)
| File | Contents | Status |
|------|----------|--------|
| `colors.ts` | Whites, blacks, accent (#3A7C9D), restricted colors | Defined |
| `typography.ts` | Eloquia fonts, 11-21px scale, 400/500/600 weights | Defined |
| `spacing.ts` | 4px grid, component spacing, radii | Defined |
| `shadows.ts` | 5 elevation levels, glass effects, overlays | Defined |
| `forbidden.ts` | Banned phrases, icons, animations, patterns | Defined |

---

## 2. UI PRIMITIVES LAYER (shadcn/radix)

### Base Components
```
src/components/ui/
├── alert-dialog.tsx      # Confirmation dialogs
├── button.tsx            # Button variants (default, outline, ghost, secondary)
├── checkbox.tsx          # Form checkbox
├── dialog.tsx            # Modal base
├── dropdown-menu.tsx     # Dropdown menus
├── input.tsx             # Text input
├── label.tsx             # Form labels
├── Pagination.tsx        # List pagination
├── select.tsx            # Select dropdown
├── sonner.tsx            # Toast notifications
├── SortControls.tsx      # Sort UI
├── textarea.tsx          # Text area
└── tooltip.tsx           # Tooltips (NOTE: forbidden per brand)
```

**Migration Priority:** HIGH
- These components use shadcn defaults
- Must be restyled to use celeste tokens only
- No zinc, gray, slate, or other Tailwind defaults

---

## 3. CELESTE PRIMITIVES LAYER (Brand-Specific)

### Custom Brand Components
```
src/components/celeste/
├── index.ts              # Barrel export
├── ActionDropdown.tsx    # Action menu
├── AuditRecord.tsx       # Immutable record display
├── EntityLine.tsx        # Entity reference line
├── MutationPreview.tsx   # Preview before commit
├── ResultCard.tsx        # Search result card
├── SignaturePrompt.tsx   # Signature collection
├── StatusLine.tsx        # Status indicator
└── UncertaintySelector.tsx # Confidence selection
```

**Migration Priority:** HIGH
- These ARE the brand expression
- Must implement READ vs MUTATE distinction
- Must follow commitment ritual pattern

---

## 4. LENS CARDS LAYER (Domain-Specific)

### Result Cards by Lens Type
```
src/components/cards/
├── ChecklistCard.tsx     # Checklist lens
├── DocumentCard.tsx      # Document lens
├── EquipmentCard.tsx     # Equipment lens
├── FaultCard.tsx         # Fault lens (most complex)
├── FleetSummaryCard.tsx  # Fleet overview
├── HandoverCard.tsx      # Handover lens
├── HandoverItemCard.tsx  # Handover items
├── HORTableCard.tsx      # Hours of Rest
├── PartCard.tsx          # Parts/Inventory lens
├── PurchaseCard.tsx      # Purchase orders
├── ReceivingCard.tsx     # Receiving lens
├── SmartSummaryCard.tsx  # AI summaries
├── WorklistCard.tsx      # Worklist lens
└── WorkOrderCard.tsx     # Work order lens
```

**Migration Priority:** CRITICAL
- Each lens must follow card anatomy invariants
- Actions must be server-driven
- READ vs MUTATE must be visually distinct
- Severity/status indicators must use token colors only

### Card Anatomy (Must Be Uniform)
```
┌─────────────────────────────────────┐
│ [severity dot] [type icon]          │  ← Header slot
│ Title                        [badge]│  ← Title slot
│ Secondary text                      │
│ Description (truncated)             │  ← Body slot
│ Meta: reporter · date               │  ← Metadata slot
│                                     │
│ [Action] [Action] [Action] [→]      │  ← Actions slot
└─────────────────────────────────────┘
```

---

## 5. SPOTLIGHT LAYER (Search Interface)

### Search Components
```
src/components/spotlight/
├── index.ts              # Barrel export
├── MicroactionButton.tsx # Action buttons in search
├── SpotlightPreviewPane.tsx # Preview pane
├── SpotlightResultRow.tsx   # Individual result row
└── SpotlightSearch.tsx      # MAIN SEARCH BAR - most important surface
```

### Supporting Search Files
```
src/lib/
└── spotlightGrouping.ts  # Domain grouping logic (13 domains)
```

**Migration Priority:** WEEK 1
- SpotlightSearch.tsx is THE interface
- Must be rebuilt with tokens only
- No hardcoded values allowed

---

## 6. MODALS LAYER (Mutation Flows)

### Mutation Modals (33 total)
```
src/components/modals/
├── index.ts                    # Barrel export
├── AcknowledgeFaultModal.tsx
├── AddNoteModal.tsx
├── AddPartModal.tsx
├── AddPhotoModal.tsx
├── AddToHandoverModal.tsx
├── AddToHandoverQuickModal.tsx
├── AddWorklistTaskModal.tsx
├── ApplyCrewTemplateModal.tsx
├── AssignWorkOrderModal.tsx
├── CompleteWorkOrderModal.tsx
├── ComplianceWarningModal.tsx
├── CreateCrewTemplateModal.tsx
├── CreateMonthlySignoffModal.tsx
├── CreatePurchaseRequestModal.tsx
├── DiagnoseFaultModal.tsx
├── EditEquipmentDetailsModal.tsx
├── EditFaultDetailsModal.tsx
├── EditHandoverSectionModal.tsx
├── EditInvoiceAmountModal.tsx
├── EditPartQuantityModal.tsx
├── EditWorkOrderDetailsModal.tsx
├── FaultHistoryModal.tsx
├── LinkEquipmentToFaultModal.tsx
├── LinkPartsToWorkOrderModal.tsx
├── LogDeliveryReceivedModal.tsx
├── LogPartUsageModal.tsx
├── MonthlySignoffModal.tsx
├── OrderPartModal.tsx
├── ReportFaultModal.tsx
├── ShowManualSectionModal.tsx
├── SuggestPartsModal.tsx
└── UpdateHoursOfRestModal.tsx

src/components/actions/modals/
└── CreateWorkOrderModal.tsx
```

**Migration Priority:** WEEK 3
- All modals must follow commitment ritual
- Preview → Sign → Commit → Record
- Heavier visual weight than read actions
- Overlay dimming per spec (85% opacity)

---

## 7. ACTION SYSTEM LAYER

### Action Components
```
src/components/actions/
├── ActionButton.tsx           # Single action button
├── ActionModal.tsx            # Action modal wrapper
├── ActionPanel.tsx            # Action grid/list
├── ConfirmationDialog.tsx     # Confirm before execute
├── CreateWorkOrderFromFault.tsx
└── modals/
    └── CreateWorkOrderModal.tsx
```

### Action Logic
```
src/lib/microactions/
├── index.ts              # Barrel export
├── registry.ts           # 57 action definitions
├── types.ts              # Action type definitions
├── executor.ts           # Action execution
├── confirmation.ts       # Confirmation logic
├── triggers.ts           # Deterministic triggers
├── validator.ts          # Input validation
├── handlers/
│   ├── index.ts
│   ├── compliance.ts     # Compliance actions
│   ├── equipment.ts      # Equipment actions
│   ├── faults.ts         # Fault actions
│   ├── handover.ts       # Handover actions
│   ├── hours_of_rest.ts  # HOR actions
│   ├── inventory.ts      # Inventory actions
│   ├── procurement.ts    # Procurement actions
│   └── workOrders.ts     # Work order actions
└── hooks/
    ├── index.ts
    ├── useAction.ts
    ├── useActionDecisions.ts  # Server-driven decisions
    ├── useActionState.ts
    └── useAvailableActions.ts
```

---

## 8. SITUATION/CONTEXT LAYER

### Situation Components
```
src/components/situations/
├── DocumentSituationView.tsx
├── EmailSituationView.tsx
├── SituationCard.tsx
├── SituationPanel.tsx
└── SituationRouter.tsx
```

### Context Navigation
```
src/components/context-nav/
├── AddRelatedModal.tsx
├── RelatedPanel.tsx
└── ViewerHeader.tsx
```

### Situation Logic
```
src/lib/situations/
├── index.ts
├── types.ts
├── intent-parser.ts
├── situation-engine.ts
└── hooks/
    ├── index.ts
    ├── useSituation.ts
    └── useSituationContext.ts
```

---

## 9. STATE MANAGEMENT LAYER

### Contexts
```
src/contexts/
├── AuthContext.tsx       # Authentication state
├── NavigationContext.tsx # Viewer stack navigation
└── SurfaceContext.tsx    # Panel states (search, email, context)
```

### Providers
```
src/providers/
├── MicroactionsProvider.tsx  # Action system
└── QueryProvider.tsx         # React Query
```

---

## 10. HOOKS LAYER

### Data Fetching Hooks
```
src/hooks/
├── useActionHandler.ts   # Action execution
├── useActionQuery.ts     # Action data fetching
├── useAuth.ts            # Auth hook
├── useAuthSession.ts     # Session management
├── useCelesteSearch.ts   # Search hook (CRITICAL)
├── useDashboardData.ts   # Dashboard data
├── useDebounce.ts        # Debounce utility
├── useEmailData.ts       # Email fetching
├── useEmailDataDebug.ts  # Debug helper
├── useFilters.ts         # Filter state
├── useListViews.ts       # List view state
├── useSearch.ts          # Search state
├── useSecureDocument.ts  # Document access
└── useSituationState.ts  # Situation state
```

---

## 11. APP ROUTES LAYER

### Single Surface (Primary)
```
src/app/app/
├── page.tsx              # THE SINGLE SURFACE - /app
├── ContextPanel.tsx      # Right panel
├── DeepLinkHandler.tsx   # E2E testing
└── EmailOverlay.tsx      # Email panel
```

### Supporting Routes
```
src/app/
├── page.tsx              # Root redirect
├── layout.tsx            # Root layout
├── not-found.tsx         # 404
├── login/
│   ├── page.tsx
│   └── LoginContent.tsx
├── auth/callback/
├── email/inbox/
├── email/search/
├── equipment/[id]/
├── faults/[id]/
├── parts/[id]/
├── work-orders/[id]/
├── integrations/
└── open/
```

### Archived (Legacy)
```
src/app/_archived/        # DO NOT USE - legacy dashboard pages
```

---

## 12. DEPENDENCY FLOW

```
┌─────────────────────────────────────────────────────────────────┐
│                        tailwind.config.ts                       │
│                    (SINGLE SOURCE OF TRUTH)                     │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      src/styles/tokens/*                        │
│         (TypeScript tokens + CSS variables export)              │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      src/styles/globals.css                     │
│              (CSS variables, base styles, animations)           │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│      src/components/ui/*     │  │   src/components/celeste/*   │
│      (shadcn primitives)     │  │    (brand primitives)        │
└──────────────────────────────┘  └──────────────────────────────┘
                    │                         │
                    └────────────┬────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    src/components/cards/*                       │
│                    src/components/spotlight/*                   │
│                    src/components/modals/*                      │
│                       (surface components)                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        src/app/app/page.tsx                     │
│                    (THE SINGLE SURFACE - /app)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 13. CONTRAST RATIO REQUIREMENTS (WCAG)

### Minimum Ratios
| Text Type | Ratio Required | Standard |
|-----------|---------------|----------|
| Normal text | 4.5:1 | AA |
| Large text (18pt+, 14pt bold) | 3:1 | AA |
| Enhanced (all text) | 7:1 | AAA |

### Current Palette Contrast (on #0A0A0A background)
| Token | Hex | Contrast | Pass AA? |
|-------|-----|----------|----------|
| textTitle | #EFEFF1 | ~18:1 | YES |
| textPrimary | #DADDE0 | ~15:1 | YES |
| textSecondary | #8A9196 | ~6:1 | YES |
| textMuted | #6A6E72 | ~4:1 | BORDERLINE |
| textDisabled | #4A4E52 | ~2.5:1 | NO (decorative only) |
| accent | #3A7C9D | ~4.5:1 | YES |

### Current Palette Contrast (on #EFEFF1 background)
| Token | Hex | Contrast | Pass AA? |
|-------|-----|----------|----------|
| textTitleLight | #0B0D0F | ~17:1 | YES |
| textPrimaryLight | #1A1D1F | ~14:1 | YES |
| textSecondaryLight | #8A9196 | ~3.5:1 | LARGE TEXT ONLY |

---

## 14. MIGRATION SCOPE ESTIMATE

### File Counts by Category
| Category | Files | Brand-Critical? |
|----------|-------|-----------------|
| UI Primitives | 12 | HIGH |
| Celeste Primitives | 8 | CRITICAL |
| Lens Cards | 14 | CRITICAL |
| Spotlight | 4 | CRITICAL |
| Modals | 34 | HIGH |
| Actions | 6 | HIGH |
| Situations | 5 | MEDIUM |
| Contexts | 3 | LOW |
| Hooks | 14 | LOW |
| Pages | 8 | MEDIUM |
| **TOTAL** | **108** | - |

### Hardcoded Value Audit (To Be Completed)
- [ ] Hex colors in component files
- [ ] Tailwind non-celeste classes (zinc, gray, slate, blue)
- [ ] Inline styles with hardcoded values
- [ ] Magic numbers for spacing/sizing

---

## 15. LENS INVARIANTS

### What Must Be Uniform Across All Lenses
1. Card padding: `p-4` (16px)
2. Border radius: `rounded-lg` (12px)
3. Shadow: `shadow-md` (elevation-2)
4. Title typography: `text-[15px] font-semibold`
5. Meta typography: `text-[12px] text-celeste-text-secondary`
6. Action button styling: `h-8 px-3 text-[13px]`
7. Status dot size: 8px
8. Icon size in actions: 14px (h-3.5 w-3.5)

### What May Vary Per Lens
1. Which fields are shown
2. Field emphasis (which is title vs meta)
3. Which actions are available (server-driven)
4. Severity/status color mapping
5. Related items panel content

---

## 16. FILES REQUIRING HARDCODED VALUE AUDIT

Priority files to check for hardcoded values:

```
CRITICAL (Search Interface):
- src/components/spotlight/SpotlightSearch.tsx
- src/components/spotlight/SpotlightResultRow.tsx
- src/app/app/page.tsx

HIGH (Cards):
- src/components/cards/*.tsx (all 14 files)
- src/components/celeste/*.tsx (all 8 files)

HIGH (UI Primitives):
- src/components/ui/button.tsx
- src/components/ui/dialog.tsx
- src/components/ui/input.tsx

MEDIUM (Modals):
- src/components/modals/*.tsx (all 34 files)

MEDIUM (Actions):
- src/components/actions/*.tsx (all 6 files)
```

---

## 17. HARDCODED VALUE AUDIT (COMPLETED)

### Summary
| Pattern | Occurrences | Files | Priority |
|---------|-------------|-------|----------|
| Hex colors (#XXXXXX) | 186 | 15 | HIGH |
| `zinc-*` classes | 238 | 24 | CRITICAL |
| `gray-*` classes | 50 | 1 | HIGH |
| `red-*` classes | 313 | 63 | CRITICAL |
| `green-*` classes | 91 | 35 | HIGH |
| `blue-*` classes | 0 | 0 | OK |
| **TOTAL** | **878** | - | - |

### Hex Color Hotspots (186 occurrences)
| File | Count | Notes |
|------|-------|-------|
| `email/_legacy/EmailSearchView.tsx` | 70 | LEGACY - deprioritize |
| `actions/ActionModal.tsx` | 21 | HIGH priority |
| `ThreadLinksPanel.tsx` | 29 | HIGH priority |
| `document/DocumentViewer.tsx` | 14 | MEDIUM |
| `situations/DocumentSituationView.tsx` | 15 | MEDIUM |
| `AuthDebug.tsx` | 12 | LOW (debug only) |
| `withAuth.tsx` | 9 | LOW |
| `SpotlightSearch.tsx` | 6 | CRITICAL |

### Zinc Classes Hotspots (238 occurrences)
| File | Count | Notes |
|------|-------|-------|
| `EmailThreadViewer.tsx` | 29 | HIGH |
| `RelatedEmailsPanel.tsx` | 20 | HIGH |
| `ModuleContainer.tsx` | 18 | MEDIUM |
| `PredictiveRiskModule.tsx` | 17 | MEDIUM |
| `EmailInboxView.tsx` | 14 | HIGH |
| `LinkEmailModal.tsx` | 12 | MEDIUM |
| `SituationCard.tsx` | 11 | HIGH |
| `CrewNotesModule.tsx` | 10 | MEDIUM |
| `HandoverStatusModule.tsx` | 10 | MEDIUM |
| `SituationPanel.tsx` | 9 | HIGH |
| `ControlCenter.tsx` | 9 | MEDIUM |
| `FaultCard.tsx` | 7 | CRITICAL |
| `WorkOrderCard.tsx` | 7 | CRITICAL |

### Red Classes Hotspots (313 occurrences)
| File | Count | Notes |
|------|-------|-------|
| `EditFaultDetailsModal.tsx` | 18 | Must use `restricted.red` |
| `AddPartModal.tsx` | 15 | Must use `restricted.red` |
| `LogPartUsageModal.tsx` | 15 | Must use `restricted.red` |
| `CreatePurchaseRequestModal.tsx` | 13 | Must use `restricted.red` |
| `EditPartQuantityModal.tsx` | 12 | Must use `restricted.red` |
| `EditWorkOrderDetailsModal.tsx` | 12 | Must use `restricted.red` |
| `CompleteWorkOrderModal.tsx` | 11 | Must use `restricted.red` |
| `OrderPartModal.tsx` | 11 | Must use `restricted.red` |

### Green Classes Hotspots (91 occurrences)
| File | Count | Notes |
|------|-------|-------|
| `EmailSurface.tsx` | 10 | Must use `restricted.green` |
| `DiagnoseFaultModal.tsx` | 7 | Must use `restricted.green` |
| `BriefingContent.tsx` | 5 | ARCHIVED |
| `LogPartUsageModal.tsx` | 5 | Must use `restricted.green` |

---

## 18. MIGRATION COMPLEXITY ASSESSMENT

### Files by Complexity
| Complexity | Count | Criteria |
|------------|-------|----------|
| CRITICAL | 8 | >20 hardcoded values, core UX surface |
| HIGH | 24 | 10-20 hardcoded values |
| MEDIUM | 35 | 5-10 hardcoded values |
| LOW | ~40 | <5 hardcoded values |

### Critical Files (Must Fix Week 1-2)
1. `SpotlightSearch.tsx` - THE interface
2. `FaultCard.tsx` - Primary lens card
3. `WorkOrderCard.tsx` - Primary lens card
4. `EmailThreadViewer.tsx` - High visibility
5. `ModuleContainer.tsx` - Dashboard foundation
6. `SituationCard.tsx` - Context display
7. `SituationPanel.tsx` - Context panel
8. `ControlCenter.tsx` - Dashboard

### High Priority Files (Week 2-3)
1. All modal files with >10 occurrences
2. All card files
3. Email components
4. Dashboard modules

---

## 19. TOKEN MIGRATION STRATEGY

### Phase 1: Lock Tailwind Config
```typescript
// tailwind.config.ts - ONLY THESE VALUES ALLOWED
colors: {
  celeste: {
    // Backgrounds
    black: '#0A0A0A',
    white: '#EFEFF1',
    surface: '#121212',
    panel: '#1A1A1A',

    // Text
    'text-title': '#EFEFF1',
    'text-primary': '#DADDE0',
    'text-secondary': '#8A9196',
    'text-muted': '#6A6E72',
    'text-disabled': '#4A4E52',

    // Accent (functional only)
    accent: '#3A7C9D',
    'accent-hover': '#327189',

    // Restricted (specific contexts)
    warning: '#9D3A3A',
    success: '#3A9D5C',
    caution: '#9D8A3A',
    inspect: '#9D6B3A',

    // Borders
    border: '#2A2A2A',
    'border-subtle': 'rgba(255, 255, 255, 0.06)',
  }
}
```

### Phase 2: Find & Replace Patterns
| From | To |
|------|-----|
| `bg-zinc-900` | `bg-celeste-black` |
| `bg-zinc-800` | `bg-celeste-surface` |
| `bg-zinc-700` | `bg-celeste-panel` |
| `text-zinc-100` | `text-celeste-text-title` |
| `text-zinc-200` | `text-celeste-text-primary` |
| `text-zinc-400` | `text-celeste-text-secondary` |
| `text-zinc-500` | `text-celeste-text-muted` |
| `text-zinc-600` | `text-celeste-text-disabled` |
| `text-red-*` | `text-celeste-warning` |
| `bg-red-*` | `bg-celeste-warning/10` |
| `text-green-*` | `text-celeste-success` |
| `bg-green-*` | `bg-celeste-success/10` |
| `border-zinc-*` | `border-celeste-border` |

### Phase 3: Validate Contrast
- Run contrast checker on all token pairs
- Ensure 4.5:1 minimum for body text
- Ensure 3:1 minimum for large text

---

## 20. READ vs MUTATE VISUAL SPECIFICATION

### The Principle
READ actions are inline and lightweight — they feel like text links.
MUTATE actions are contained and separated — they feel like buttons.
Weight comes from border + background + padding, NOT from shadows.
Shadows are reserved for elevation changes (modals, commitment states).

### Exact Styling

| Aspect | READ Action | MUTATE Action |
|--------|-------------|---------------|
| Background | `transparent` | `bg-celeste-surface` |
| Border | None | `border border-celeste-border` |
| Shadow | None | None (shadow at commitment stage) |
| Font weight | `font-normal` (400) | `font-medium` (500) |
| Text color | `text-celeste-text-secondary` | `text-celeste-text-primary` |
| Hover | `hover:text-celeste-text-primary` | `hover:bg-celeste-panel` |
| Padding | `px-2 py-1` (minimal) | `px-3 py-1.5` (more room) |

### Implementation Classes

```tsx
// READ action button
className="bg-transparent text-celeste-text-secondary font-normal px-2 py-1
           hover:text-celeste-text-primary transition-colors"

// MUTATE action button
className="bg-celeste-surface border border-celeste-border text-celeste-text-primary
           font-medium px-3 py-1.5 rounded-celeste-sm hover:bg-celeste-panel transition-colors"
```

---

## 21. CORRECTED MIGRATION MAP

### Restricted Color Mapping (No Aliases)

| From | To | Hex |
|------|-----|-----|
| `red-*`, `rose-*` | `restricted-red` | #9D3A3A |
| `green-*`, `emerald-*` | `restricted-green` | #3A9D5C |
| `yellow-*`, `amber-*` | `restricted-yellow` | #9D8A3A |
| `orange-*` | `restricted-orange` | #9D6B3A |

### Opacity Patterns

| From | To |
|------|-----|
| `bg-red-500/10` | `bg-restricted-red/10` |
| `bg-green-500/10` | `bg-restricted-green/10` |
| `text-red-500` | `text-restricted-red` |
| `text-green-500` | `text-restricted-green` |
| `border-red-*` | `border-restricted-red` |
| `focus:ring-red-*` | `focus:ring-restricted-red` |

---

## 22. EXECUTION DECISIONS

### Task 1.2 — SKIPPED
Going gradual. Keep app running. Lock down Tailwind in Phase 9.

### Tooltip.tsx — MIGRATE + FLAG
```tsx
// BRAND NOTE: Tooltips are discouraged per brand doctrine. Prefer inline context.
```

### Legacy Files — IGNORE + FLAG
```tsx
// LEGACY: Not migrated to celeste tokens. Scheduled for removal.
```
Files to flag:
- `email/_legacy/EmailSearchView.tsx`
- `app/_archived/*`

### Build/Test Cadence
- `npm run build` after every PHASE (not every task)
- Visual check after Phases 2, 3, 5, 7
- Fix breaks before proceeding to next phase

### Timeline
4 weeks. Don't compress. Phases 6-7 will go faster; buffer for Phases 4-5.

