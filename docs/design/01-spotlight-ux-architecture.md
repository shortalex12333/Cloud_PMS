# Spotlight UX: mental model + architecture (notes)

Goal: Copy the **experience** (keyboard-first palette + grouped results + preview + fast ranking), and get close to Apple’s “clean minimalism”.

## Spotlight is two big things
1) **Search system**
- Indexing (files + app content)
- Query parsing + ranking
- Result “cards” with metadata, icons, actions

2) **Presentation system (UI)**
- A floating, transient panel that becomes **key** without taking over as a normal main window
- “Glass” / translucency material
- Tight typography + spacing + motion

## Why web clones look “SaaS-y”
Typical causes:
- Generic shadows and borders
- Wrong type scale and font metrics
- Over-rounded corners
- Blur without the right tint/noise/contrast behavior
- Icons with inconsistent optical sizing
- Motion curves that feel like a website, not a system UI

## Key insight
Framework choice (React/Next/Vite) is not the root issue.
The “Apple feel” comes from:
- System materials + vibrancy recipes (macOS)
- Very specific layout and typography discipline
- Correct window/focus behavior (NSPanel patterns)

## Practical paths
### A) If you’re building a macOS app
Use AppKit/SwiftUI and native materials. You’ll get most of the “Apple feel” for free.

### B) If you’re building a web app that imitates the look
You can get close, but you must intentionally recreate:
- Material layering (blur + tint + subtle noise + contrast)
- Typography metrics (system font stack + correct line-height)
- Interaction polish (keyboard/focus, escape-to-dismiss, anim timing)

---
