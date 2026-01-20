# Email UX Fix - Inline List Beneath Search Bar

**Date:** 2026-01-20
**Status:** ✅ IMPLEMENTED

---

## Requirement

> "Email must be a list beneath search bar, not left sidebar"

---

## Change Summary

Modified `SpotlightSearch.tsx` to show email list inline beneath the search bar instead of in a separate left sidebar.

---

## Changes Made

### 1. Added EmailInboxView import
```tsx
import { EmailInboxView } from '@/components/email/EmailInboxView';
```

### 2. Added showEmailList state
```tsx
const [showEmailList, setShowEmailList] = useState(false);
```

### 3. Modified Email button handler
```tsx
// Before: Triggered left sidebar
onClick={() => {
  onClose?.();
  if (onEmailClick) {
    onEmailClick();
  }
}}

// After: Shows inline email list
onClick={() => {
  setShowEmailList(!showEmailList);
  clear();
}}
```

### 4. Added inline email list rendering
```tsx
{/* Email List (beneath search bar per UX doctrine) */}
{showEmailList && !hasQuery && (
  <div className="max-h-[420px] overflow-y-auto spotlight-scrollbar">
    <EmailInboxView className="p-4" />
  </div>
)}
```

### 5. Auto-hide on search
```tsx
onChange={(e) => {
  handleQueryChange(e.target.value);
  if (e.target.value) setShowEmailList(false);
}}
```

---

## Behavior

| Action | Before | After |
|--------|--------|-------|
| Click Email button | Opens left sidebar | Shows inline list beneath search |
| Start typing search | Sidebar stays open | Email list hides, shows results |
| Click Email again | N/A | Toggles email list visibility |

---

## Files Modified

- `apps/web/src/components/spotlight/SpotlightSearch.tsx`

---

## UI Layout After Change

```
┌─────────────────────────────────────────┐
│              Search Bar                 │
├─────────────────────────────────────────┤
│                                         │
│     Email Inbox (when Email clicked)    │
│     - Unlinked threads                  │
│     - Link to Work Order buttons        │
│                                         │
│         OR                              │
│                                         │
│     Search Results (when typing)        │
│     - Equipment                         │
│     - Documents                         │
│     - Work Orders                       │
│                                         │
└─────────────────────────────────────────┘
```

---

## Note

The left sidebar EmailPanel still exists but is no longer the primary way to access email. It can be removed in a future cleanup if desired.
