# Reverse Engineering NSVisualEffectView (why Apple “glass” looks right)

Source:
- https://oskargroth.com/blog/reverse-engineering-nsvisualeffectview

## What it’s useful for
This is one of the most actionable engineering write-ups for understanding why:
- your CSS blur looks “fake”
- Apple’s material looks “expensive” and consistent

## Core findings (paraphrased)
- `NSVisualEffectView` doesn’t “compute” materials from scratch.
- It loads **pre-defined material recipes** from **CoreUI** (private framework).
- Recipes live in **compiled asset catalog** `.car` files and include:
  - filter values
  - tint colors
  - blend modes
  - variants for active/inactive + light/dark + accessibility contrast

Short quote (under 25 words):
> “NSVisualEffectView loads pre-defined material configurations from CoreUI…” (Oskar Groth)

## Why this matters to you
### If you’re native macOS
Use the system materials. Don’t attempt to out-Apple Apple.

### If you’re web
You need to recreate the *effect stack*, not just blur:
- blur + saturation/brightness tuning
- correct tint overlay
- subtle noise/grain
- contrast-aware text/icon styling
- active/inactive state differences

## Suggested “web approximation” recipe (conceptual)
- Backdrop blur layer
- Saturation adjustment layer
- Tint overlay (opacity varies with light/dark)
- 1–2% noise
- Inner stroke at low opacity (instead of heavy shadow)
- Shadow extremely subtle (or none)

---
