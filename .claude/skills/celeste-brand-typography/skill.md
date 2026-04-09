---
name: celeste-brand-typography
description: >
  Invoke before ANY branded content, homepage work, marketing material, PDF generation,
  presentation design, or UX decision on celeste-homepage-webflow. Loads the complete
  four-font typography system: Eloquia Display (headlines), DM Sans (body), Cormorant
  Garamond italic (accent), IBM Plex Mono (system voice). Prevents font drift, wrong
  weights, and misuse of accent type.
trigger: >
  Any of: editing celeste-homepage-webflow, creating branded PDFs or decks,
  designing marketing pages, choosing headline fonts, writing CTA copy,
  producing any Celeste-branded document or presentation, front-end UX for
  homepage or landing pages.
---

# CelesteOS Brand Typography System

## Principle

**Contrast creates hierarchy.** Four fonts, each with a distinct role. An editorial display font for statements, a clean sans for readability, an italic serif for emotion, and a monospace for technical credibility.

---

## The Four Fonts

### 1. Eloquia Display — The Brand Voice

Commercial display typeface by Typekiln. Installed locally; bundled as WOFF2 in `celeste-homepage-webflow/fonts/`. Not on Google Fonts.

**Role:** Headlines and section titles. Refined, geometric, confident without being cold. Signals quality and precision.

| Element | CSS class | Size | Weight | Reasoning |
|---------|-----------|------|--------|-----------|
| Hero headline | `.heading` | 56px (desktop) | **300 (Light)** | Large canvas → light weight is elegant, not aggressive |
| CTA image heading | `.cta-heading` | 56px | **300 (Light)** | Same — big canvas, light touch |
| Footer CTA heading | `.cta-heading` (footer) | 28px | **300 (Light)** | Intimate scale, reads as invitation |
| Section titles | `.about-heading`, `.heading-service`, `.heading--benefits`, `.impact-heading` | 36–48px | **400 (Regular)** | Mid-size needs weight to hold page. Light at 36px is anaemic |
| Footer email | `.footer-heading` | 48px | **400 (Regular)** | Functional heading, needs presence |

**Weight rule:** Light (300) at ≥48px. Regular (400) at 36–48px. Medium (500) only if you need to shout — we don't.

**Available weights (bundled):** Light (300) + Italic, Regular (400) + Italic, Medium (500) + Italic

**CSS variable:** `--_size---font-family-display`
**Fallback:** `'Eloquia Display', system-ui, -apple-system, sans-serif`

---

### 2. DM Sans — The Workhorse

Geometric sans-serif by Colophon Foundry. Google Fonts.

**Role:** Everything that isn't a headline, accent, or system data. Body paragraphs, descriptions, button text, card text, benefit descriptions, testimonials.

Body text should be invisible infrastructure, not decoration.

**Weights:** 300 (Light), 400 (Regular), 500 (Medium)
**CSS variable:** `--_size---font-family`
**Fallback:** `'DM Sans', sans-serif`

---

### 3. Cormorant Garamond Italic — The Emotional Accent

High-contrast serif by Christian Thalmann. Google Fonts. **Only italic cuts used.**

**Role:** 4–6 words per page maximum. Creates a visual "catch" — the eye pauses. The typographic equivalent of a teal highlight.

**Current accent instances (homepage):**
| Text | Why |
|------|-----|
| *"complexity."* | The core promise |
| *"the vessel,"* | Vessel-centric philosophy |
| *"in the vessel."* | Callback — knowledge stays aboard |
| *"Sources,"* | The differentiator |
| *"limited."* | Scarcity signal |
| *"we should talk."* | Warmth, invitation |

**Rule:** Never use Cormorant for full sentences or paragraphs. Max 3–4 words. It's an accent, not a body font.

**Weight:** 300 italic only
**CSS variable:** `--_size---font-family-accent`
**Fallback:** `'Cormorant Garamond', Georgia, serif`
**CSS class:** `.accent` (applies font + italic + teal colour `#2B7BA3`)

---

### 4. IBM Plex Mono — The System Voice

Monospace by Mike Abbink / IBM. Google Fonts.

**Role:** Says "system" — data, precision, engineering. Section numbers, nav links, artifact UI, labels, timestamps, technical identifiers.

**Weights:** 400 (Regular), 500 (Medium), 600 (SemiBold)
**CSS variable:** `--_size---font-family-mono`
**Fallback:** `'IBM Plex Mono', monospace`

---

## Decision Tree (Brand Typography)

Before setting any font on branded material:

1. **Is this a headline or section title?** → Eloquia Display
   - ≥48px → weight 300 (Light)
   - 36–48px → weight 400 (Regular)
2. **Is this body text, descriptions, buttons?** → DM Sans
3. **Is this 1–4 accent words meant to create emotional pause?** → Cormorant Garamond 300 italic + teal `#2B7BA3`
4. **Is this a system identifier, number, code, nav label, timestamp?** → IBM Plex Mono
5. **Unsure?** → DM Sans (the safe default)

---

## For Branded Documents (PDF, Decks, Print)

| Context | Font | Weight | Size |
|---------|------|--------|------|
| Document title / cover | Eloquia Display | Light (300) | ≥28pt |
| Section headings | Eloquia Display | Regular (400) | 18–24pt |
| Body text | DM Sans | Regular (400) | 10–12pt |
| Captions, footnotes | DM Sans | Light (300) | 8–9pt |
| Key emphasis (1–3 words) | Cormorant Garamond | Light Italic (300i) | Match body size, teal #2B7BA3 |
| Data, codes, IDs | IBM Plex Mono | Regular (400) | Match body size |

---

## Key Files

| File | Controls |
|------|----------|
| `celeste-homepage-webflow/index.html` lines 39–81 | @font-face declarations (Eloquia WOFF2) |
| `celeste-homepage-webflow/index.html` line 25 | WebFont.load() for Google Fonts |
| `celeste-homepage-webflow/index.html` lines 82–99 | `.accent` and `em` styling |
| `celeste-homepage-webflow/css/celeste7homepage.webflow.css` lines 1–15 | CSS custom properties |
| `celeste-homepage-webflow/css/celeste7homepage.webflow.css` lines 3956–3980 | Font family + weight assignments |
| `celeste-homepage-webflow/css/celeste7homepage.webflow.css` line 4655 | Footer CTA heading |
| `celeste-homepage-webflow/fonts/` | 6 WOFF2 files (Eloquia Light/Regular/Medium + italics) |

---

## Anti-patterns (never do these)

- Using Eloquia Display for body text or paragraphs
- Using Cormorant for more than 4 words at a time
- Using DM Sans for headlines (that's what Eloquia is for)
- Using weight 500+ on Eloquia at large sizes (aggressive, not the brand)
- Using weight 300 on Eloquia at ≤36px (anaemic, loses authority)
- Putting accent (Cormorant) text without the teal colour
- Adding a fifth font

---

## Relationship to PMS App Typography

The **PMS app** (Cloud_PMS) uses Inter + Mono — see `celeste-design-philosophy` skill.
The **brand/homepage** uses Eloquia Display + DM Sans + Cormorant + Plex Mono — this skill.

These are separate systems. Don't mix them. The PMS app is a tool (Inter = neutral workhorse). The homepage is a brand surface (Eloquia = editorial voice).
