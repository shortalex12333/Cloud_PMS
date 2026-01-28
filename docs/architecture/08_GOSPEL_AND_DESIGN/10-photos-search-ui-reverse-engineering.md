# Reverse Engineering Photos’ Search UI (iOS) — transferable lessons

Source:
- https://sebvidal.com/blog/reverse-engineering-photos-search-ui/

## What it’s useful for
Not Spotlight on macOS, but a very relevant **“Apple search UI”** reverse engineering approach:
- where Apple uses public API
- where they rely on private/internal effects
- how to think about recreating the look

## Useful transferable lessons
- “Close” is easy with a stock blur.
- “Indistinguishable” usually requires private effects or extremely careful layering.
- The unpleasant line between your blur region and the system background is a classic giveaway.

Short quote (under 25 words):
> “The bad news is this effect cannot be recreated with public API…” (Seb Vidal)

## Actionable takeaways for your Spotlight-style palette
- Avoid hard edges where materials meet content.
- Prefer gradient fades / soft transitions.
- If you’re web: design your own “signature” material rather than chasing pixel-perfect Apple.

---
