# Email UX Doctrine Fix Evidence

**Date:** 2026-01-20
**Mandate:** Email must be inline beneath search bar only. No left sidebar inbox.

---

## Changes Made

### 1. Removed Left Sidebar EmailPanel

**File:** `apps/web/src/app/app/page.tsx`

**Before:**
```tsx
<div className="relative flex h-screen overflow-hidden">
  {/* Email Panel - slides from left */}
  <Suspense fallback={<div className="w-96 bg-gray-800/50" />}>
    <EmailPanel />
  </Suspense>

  {/* Center - Spotlight Search */}
  <div className="flex-1 flex items-start justify-center pt-[15vh]">
    <SpotlightSearch onEmailClick={() => showEmail()} />
  </div>
</div>
```

**After:**
```tsx
<div className="relative flex h-screen overflow-hidden">
  {/* Center - Spotlight Search (email inline beneath search bar per UX doctrine) */}
  <div className="flex-1 flex items-start justify-center pt-[15vh]">
    <SpotlightSearch />
  </div>
</div>
```

### 2. Removed onEmailClick Prop

**File:** `apps/web/src/components/spotlight/SpotlightSearch.tsx`

- Removed `onEmailClick?: () => void` from `SpotlightSearchProps` interface
- Removed `onEmailClick` from component function parameters

---

## Email Inline Implementation

The SpotlightSearch component already had inline email implemented (lines 569-577):

```tsx
{/* Email List (beneath search bar per UX doctrine) */}
{showEmailList && !hasQuery && (
  <div
    className="max-h-[420px] overflow-y-auto overflow-x-hidden spotlight-scrollbar bg-[#1c1c1e] rounded-b-2xl"
    data-testid="email-list-inline"
  >
    <EmailInboxView className="p-4" />
  </div>
)}
```

Email access is via the Ledger dropdown (BookOpen icon) beneath the search bar.

---

## Test Results

**Before:** 169 tests passing
**After:** 169 tests passing

All E2E tests continue to pass after removing the left sidebar.

---

## UX Architecture After Fix

```
+--------------------------------------------------+
|                                                  |
|                                                  |
|              [SpotlightSearch]                   |
|              +-----------------+                 |
|              | Search Input    |                 |
|              +-----------------+                 |
|              | Email (inline)  | <- UX Doctrine  |
|              | or Search Results|                |
|              +-----------------+                 |
|                                                  |
|              [BookOpen] [Settings]               |
|                                                  |
+--------------------------------------------------+
```

- **Single surface**: /app
- **Single search bar**: SpotlightSearch
- **Email inline**: Beneath search bar, triggered by Ledger menu
- **No left sidebar inbox**: Removed

---

## Compliance Status

| Requirement | Status |
|-------------|--------|
| Remove left sidebar inbox | DONE |
| Email inline beneath search bar only | DONE |
| Tests pass after change | DONE (169/169) |
