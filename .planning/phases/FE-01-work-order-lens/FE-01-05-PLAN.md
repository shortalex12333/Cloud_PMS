---
wave: 2
depends_on: [FE-01-01]
files_modified:
  - apps/web/src/components/lens/WorkOrderLens.tsx
  - apps/web/src/components/lens/LensContainer.tsx
  - apps/web/src/styles/lens.css
autonomous: true
requirements: [WO-03]
---

# Plan FE-01-05: Full-Screen Lens Layout + Glass Transitions

## Objective

Implement full-screen lens layout (100vw × 100vh) with proper header, glass transition from search results, and back/close navigation.

## Tasks

<task id="1">
Create `LensContainer.tsx` as the full-screen wrapper:

```tsx
interface LensContainerProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}
```

Layout:
- Position: fixed, inset: 0
- Background: surface-base
- Z-index: z-modal (40)
- Overflow-y: auto for scrolling content
- Padding: 0 (header handles its own padding)
</task>

<task id="2">
Implement glass transition animation:

```css
/* Entering from search result */
.lens-enter {
  opacity: 0;
  transform: scale(0.98);
  backdrop-filter: blur(0px);
}

.lens-enter-active {
  opacity: 1;
  transform: scale(1);
  backdrop-filter: blur(20px);
  transition: all 300ms var(--ease-out);
}

/* Exiting back to search */
.lens-exit {
  opacity: 1;
  transform: scale(1);
}

.lens-exit-active {
  opacity: 0;
  transform: scale(0.98);
  transition: all 200ms ease-in;
}
```

Use React Transition Group or Framer Motion.
</task>

<task id="3">
Wire lens opening from search results:

```tsx
// In SearchResults or wherever results are displayed
const handleResultClick = (entity: SearchResult) => {
  // Log navigation to ledger
  logAction('navigate_to_lens', { entity_type: entity.type, entity_id: entity.id });

  // Open lens with transition
  setActiveLens({ type: entity.type, id: entity.id });
};
```

The lens should:
- Fade in from search result position (if possible)
- Or fade in from center with slight scale
- Cover entire viewport
</task>

<task id="4">
Implement back/close behavior:

- **Back button**: Returns to previous lens if navigation stack exists, otherwise closes
- **Close button (×)**: Always returns to search/home state
- Both log to ledger

```tsx
const handleBack = () => {
  if (navigationStack.length > 1) {
    const previous = navigationStack[navigationStack.length - 2];
    logAction('navigate_back', { from: currentLens, to: previous });
    goBack();
  } else {
    handleClose();
  }
};

const handleClose = () => {
  logAction('close_lens', { lens: currentLens });
  setActiveLens(null);
  clearNavigationStack();
};
```
</task>

<task id="5">
Ensure proper scrolling behavior:

- Body scroll locked when lens is open
- Lens content scrolls independently
- Section headers stick correctly within lens scroll context
- Mobile: prevent overscroll/bounce

```tsx
useEffect(() => {
  if (isOpen) {
    document.body.style.overflow = 'hidden';
  }
  return () => {
    document.body.style.overflow = '';
  };
}, [isOpen]);
```
</task>

<task id="6">
Test the full flow:

1. Search for "generator"
2. Click Work Order result
3. Verify glass transition (300ms)
4. Verify full-screen layout
5. Click equipment link → navigate to Equipment lens
6. Click Back → return to Work Order
7. Click Close → return to search
</task>

## Verification

```bash
# LensContainer exists
ls apps/web/src/components/lens/LensContainer.tsx

# Transition CSS exists
grep -n "lens-enter\|lens-exit" apps/web/src/styles/

# Build passes
cd apps/web && npm run build
```

## must_haves

- [ ] Lens opens full-screen (100vw × 100vh)
- [ ] Glass transition animates on open (300ms)
- [ ] Back button navigates stack
- [ ] Close button returns to search
- [ ] Body scroll locked when open
- [ ] Section headers still stick within lens
- [ ] Build passes
