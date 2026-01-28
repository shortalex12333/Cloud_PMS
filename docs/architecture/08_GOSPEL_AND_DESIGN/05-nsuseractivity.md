# NSUserActivity (Apple docs placeholder + practical notes)

Canonical URL:
- https://developer.apple.com/documentation/foundation/nsuseractivity

Note: JavaScript-rendered in this environment; use the link for the authoritative reference.

## What it’s useful for
`NSUserActivity` captures “what the user is doing” so the system can:
- resume state (handoff)
- offer suggestions
- improve ranking and recall of relevant items

In Apple’s search model, NSUserActivity is a big part of why Spotlight results feel personal and “smart”.

## What to copy for your UX
If you want Spotlight-like relevance:
- Track **recent user intents** (queries, opened items, selected actions)
- Use that to reorder results, boost certain types, and create “Top Hit”
- Don’t overdo it: “smart” should feel subtle, not creepy

Companion source (accessible):
- App Search Programming Guide (see `03-app-search-programming-guide.md`)

---
