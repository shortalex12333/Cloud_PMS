# WWDC25: “Build an AppKit app with the new design” (Liquid Glass + structural UI)

Source (Apple video page with transcript):
- https://developer.apple.com/videos/play/wwdc2025/310/

## What it’s useful for
Apple’s own explanation of the **new macOS design system** and how AppKit supports it (including search controls, glass materials, grouping, and “edge effects”).

## High-value takeaways (paraphrased)
- Apple is pushing a common foundation for macOS UI with refreshed materials and controls.
- Toolbars/sidebars sit on glass material and “float” above content.
- The system automatically groups toolbar items onto shared glass surfaces.
- The glass adapts to content brightness behind it (light/dark switching).
- There’s an overlap “scroll edge effect” that provides legibility where glass overlaps scrolling content.
- New APIs exist to manage corner avoidance and concentricity (layout regions, safe area behavior).

Tiny quote (under 25 words):
> “A key element… is the Liquid Glass material, a translucent surface…” (WWDC25 transcript)

## Why this matters for copying Spotlight’s vibe
Spotlight-like UIs increasingly align with this:
- floating, translucent surfaces
- strict concentric corner radii
- minimal separators + subtle grouping

## What to do with this info
If you’re building native:
- adopt these patterns and let the OS render the material

If you’re building web:
- copy the grouping + concentricity logic
- keep surfaces sparse and “quiet”
- let content and typography do most of the work

---
