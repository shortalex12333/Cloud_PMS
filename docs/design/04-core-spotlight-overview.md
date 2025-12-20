# Core Spotlight (Apple docs placeholder + practical notes)

Canonical URL:
- https://developer.apple.com/documentation/corespotlight

Note: JavaScript-rendered; open the URL above for the full docs.

## What it’s useful for
Core Spotlight is the API layer for indexing **app-specific content** into the device’s search index (private/on-device).

## Key objects you’ll see referenced
- `CSSearchableItem`
- `CSSearchableItemAttributeSet`
- `CSSearchableIndex`

## What to copy for your UX
Spotlight results feel “native” largely because every item has:
- a well-defined type/kind
- a consistent icon
- clear primary + secondary text
- optional actions / deep links
- strong grouping (Top Hit, Applications, Documents, etc.)

If you recreate these semantics in your own system (even on web), the UI stops feeling generic.

Companion doc:
- Apple “Building a search interface for your app” (also JS-rendered)
  - https://developer.apple.com/documentation/corespotlight/building-a-search-interface-for-your-app

---
