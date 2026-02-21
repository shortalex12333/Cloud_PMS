# Visual Reference Brief — What "Good" Looks Like

> This is not philosophy. These are observable facts about ChatGPT and Apple interfaces that you must match or exceed.

---

## ChatGPT: What It Actually Does

### Spacing
- Message content sits ~40px from left/right edges on desktop
- Between messages: ~24px vertical gap
- Within a message: line-height is ~1.6, paragraph spacing is ~16px
- The content area max-width is ~768px, centered on viewport
- There is MORE empty space than content on a desktop screen. This is intentional.

### Typography
- Body text: 16px, regular weight (400), dark grey on light / light grey on dark
- No bold emphasis scattered everywhere. Bold is rare and purposeful.
- Code blocks use monospace with subtle background differentiation
- Headers within responses: weight 600, same size as body or +2px. Subtle, not screaming.
- The font is the system font stack. Nothing custom. It gets out of the way.

### Color Usage
- In light mode: the entire interface is white and warm greys. The ONLY color is the blue-green accent on the send button and user avatar. Everything else is achromatic.
- In dark mode: same principle — all surfaces are tight-range dark greys. Color appears only for interactive elements.
- There are no colored section backgrounds. No colored headers. No gradient decorations.

### Borders and Depth
- Borders are `1px solid` in a grey very close to the surface color. They define structure but don't draw attention.
- Shadows are nearly invisible. The interface feels flat. Depth comes from surface luminance steps, not from shadow effects.
- Cards (like the sidebar conversation list items) have no visible border — just a hover state that shifts the background by one luminance step.

### What This Means for Celeste Lenses
- A lens section (Notes, Parts, History) should feel like a ChatGPT conversation: content with generous padding, separated by subtle means, no heavy visual chrome.
- Section headers should be quiet — they orient, they don't decorate.
- The lens body should max-width at ~800px on desktop, centered. Not edge-to-edge.
- If you squint at the screen, you should see a calm column of content, not a dashboard of competing boxes.

---

## Apple: What It Actually Does

### Settings App (iOS/macOS) — The Closest Analog to Celeste Lenses

- Each settings "page" is a full-screen list of grouped rows
- Groups have a subtle radius (12px), a background one step lighter than the page (in light mode) or one step brighter (in dark mode)
- Rows within a group are separated by a 1px divider that does NOT extend edge-to-edge — it starts ~16px from the left (indented past the icon)
- Each row: 44-48px height, 16px horizontal padding, left-aligned label, right-aligned value/chevron
- The value text is in a lighter grey than the label. This creates hierarchy WITHOUT size difference.
- Active/selected state: subtle background highlight, no border, no shadow

### Typography
- Apple uses weight as the primary hierarchy tool, not size
  - Navigation titles: 34px bold (large title style)
  - Section content: 17px regular
  - Secondary text: 15px, lighter color
  - Captions: 13px, light grey
- The delta between sizes is small. The delta between weights and colors is large.

### Color
- `#007AFF` for ALL interactive elements. Links, toggle on-state, selected tab, buttons.
- Destructive actions: `#FF3B30` (red)
- Success: `#34C759` (green)
- No other colors in the base UI. Ever.
- This is the model for Celeste's teal: `--brand-interactive` should be the ONLY saturated color in the interface (besides status colors on pills).

### Animation
- Transitions: ~300ms with an ease-out curve that decelerates into position
- Elements slide, they don't pop. The new view pushes the old one away.
- There's a directional logic: forward navigation slides left-to-right, back slides right-to-left
- Loading: content appears in place (no spinners in the main UI). Skeleton states or shimmer.

### What This Means for Celeste
- Use weight + color to create hierarchy, not just size
- Keep size range tight: body at 14px, labels at 12-13px, titles at 22-24px. That's the whole range.
- Interactive teal should feel as commanding as Apple's #007AFF — it's the one color that says "this responds to you"
- Touch targets: 44px minimum. A button that's 32px tall is broken. Full stop.
- Transitions between lenses should have directionality — opening a lens pushes content in, closing pulls it away

---

## The Gap Between Current Celeste and These Standards

Looking at the Work Order screenshot from the current app:

| Problem | What ChatGPT/Apple would do |
|---------|----------------------------|
| UUID visible (fa847db8...) | Never show system IDs. Show entity type + title only. |
| "Pending" and "Low" styled identically | Status = colored pill. Priority = separate visual treatment (text badge or icon). Different data types, different appearance. |
| Notes section shows raw UUID under the note | Show author name + formatted date only. |
| "Parts Used" has a generic empty state icon | Contextual: "No parts linked yet — track parts to maintain accurate inventory" + [Add Part] button |
| Flat card with thin border | Use luminance step (surface-primary on surface-base) instead of border. Generous padding. Content breathes. |
| No visual hierarchy between sections | Each section separated by 24-32px of space. Headers are quiet but distinct. |
| No vital signs — user must scroll to understand entity state | 3-5 factual indicators immediately below title |
| Content feels cramped | Max-width 800px centered. 40px+ side padding. Line-height 1.6. |

---

## Density Reference

The key question: how much content per screen?

**ChatGPT:** ~5-7 visible elements per screen on desktop. Very low density. Scroll to see more.
**Apple Settings:** ~8-12 rows visible per screen. Medium density. Compact but not cramped.
**Celeste lenses should be:** Apple density in the section content (list rows, note entries) with ChatGPT-level spacing between sections. Sections have breathing room between them. Rows within sections are compact but generous. The result: the user can see 2-3 sections on screen simultaneously, each showing 3-5 items, with clear separation between sections.

---

## Quick Test: Is Your Output Good Enough?

Before submitting any lens implementation, ask:

1. **Squint test:** When you blur your eyes, do you see a calm column of content, or a dashboard of boxes?
2. **Color test:** Is teal the only saturated color (besides status pills)? If you see other colors, something is wrong.
3. **Spacing test:** Is there more empty space than content? If the screen feels "full," add more padding.
4. **UUID test:** Can you see any system identifiers? If yes, remove them.
5. **Touch test:** Could you tap every interactive element with a gloved finger on a rolling boat? If targets are small, enlarge them.
6. **5-second test:** If a new user looked at this lens for 5 seconds, would they know: what type of entity, which entity, what state it's in, and where to act? If not, the hierarchy needs work.
