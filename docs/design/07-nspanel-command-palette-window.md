# Spotlight-like command palette window behavior (NSPanel concepts)

Primary reference (Electron issue, but explains the OS concept well):
- https://github.com/electron/electron/issues/31538

## What it’s useful for
Even though this is about Electron, it captures the key macOS concept:
**Spotlight-style palettes behave like panels (NSPanel), not normal app windows.**

## Key behaviors to replicate
- Can become the **key** window (receives keyboard input) without becoming the **main** window
- Can float above other windows (including full-screen apps, depending on setup)
- Quick dismiss
- Doesn’t wreck the user’s window focus flow

Short quote (under 25 words):
> “Panel windows on macOS (NSPanel) are used to create floating command palettes (like Spotlight)…” (GitHub issue)

## Why web/electron clones often feel off
- Focus is wrong: it steals focus like a full app window
- Window management doesn’t match OS expectations
- Animations are too heavy or too slow

## Practical guidance
- If you can: implement the palette as a native panel.
- If you must do it in a browser window:
  - aggressively manage focus/blur
  - preserve the user’s prior active context
  - use escape-to-dismiss and click-outside
  - avoid heavy shadows and big rounded corners

---
