# CelesteOS UX Grammar & Visual Token Specification

**Audience:** Frontend engineers + designers
**Purpose:** Prevent drift, prevent "helpfulness", preserve trust

---

## 0. The Prime Directive (this overrides taste)

Celeste does not persuade.
Celeste does not decorate.
Celeste does not explain itself.
Celeste only reveals state and options.

If an element exists that does not:
- reveal state
- enable choice
- protect trust

…it must be removed.

---

## 1. The Visual Grammar (what things mean visually)

Celeste has no general-purpose components.
Every element belongs to one of these grammatical roles:

| Grammar Role | Meaning | Can be styled? |
|--------------|---------|----------------|
| State | What exists / what is happening | Minimal |
| Action | What the user may do | Strict |
| Transition | Movement from one state to another | Controlled |
| Commitment | Irreversible change | Heavy |
| Record | Proof of change | Immutable |

If a UI element does not map cleanly to one role, it is invalid.

---

## 2. The Canonical Search Page Layout (non-negotiable)

```
┌────────────────────────────────────────────┐
│  Search Bar                                │
│  [entities detected inline beneath]        │
├────────────────────────────────────────────┤
│                                            │
│  Result Card                               │
│                                            │
│  Result Card                               │
│                                            │
│  Result Card                               │
│                                            │
└────────────────────────────────────────────┘
```

**Rules:**
- No sidebars
- No panels
- No persistent nav
- No floating widgets
- The page scrolls vertically only

Search is the UI.

---

## 3. Entity Line (what Celeste understood)

**Purpose:** Ground trust before action.

### Visual rules
- Lives directly under search bar
- Smaller text than results
- Neutral color
- No icons
- No interactivity (read-only)

### Example
```
Understood:
• System: Main Engine
• Component: Fuel Filter
• Context: History
```

### If uncertainty exists:
```
Possible matches:
• Inventory: Box 2D
• Location: Deck Locker 2D
```

- No "Did you mean"
- No confidence language
- No highlighting

---

## 4. Result Cards (the atomic unit)

A Result Card must always follow this structure:

```
[Header — what this thing is]

[Body — the minimum useful truth]

[Primary Action]    [▼]
```

Nothing else is allowed.

---

## 5. Action Taxonomy (this is critical)

### Group A — READ / OBSERVE (default)

**Visual Token:**
- Text-only
- Normal font weight
- Same color as body text
- Inline position

**Examples:**
- View
- Open manual section
- Show history
- Compare
- Print

**Rules:**
- No confirmation
- No modal
- No delay
- Executes immediately
- Shows status line

**Status line example:**
```
Finding manual section…
```

If a READ action ever opens a modal → bug.

### Group B — MUTATE / COMMIT (restricted)

**Visual Token:**
- Slightly separated from READ
- Lower visual priority than READ
- Never inline
- Never default-highlighted

**Examples:**
- Edit inventory
- Add note
- Close work order
- Order part

**Rules:**
- Cannot execute immediately
- Must enter mutation ritual
- Must generate audit record

If a MUTATE action executes without preview → critical failure.

---

## 6. The Dropdown (▼) — exact behavior

The dropdown is not optional.

### Rules
- Only appears if more than one action exists
- Always right-aligned to primary action
- Opens downward
- No animation flair
- No icons inside

### Ordering inside dropdown
1. Remaining READ actions
2. MUTATE actions (visually separated)

### Example:
```
▼
––––––––––––
Open manual
Show history
––––––––––––
Edit inventory
Remove item
```

The divider is semantic, not decorative.

---

## 7. Mutation Ritual — exact stages & visuals

This flow is sacred.

### Stage 1 — Stage (selection)

User clicks MUTATE action.

**UI response:**
- Card expands slightly
- Background remains visible
- Nothing is written yet

No modal yet.

### Stage 2 — Preview (diff only)

This is the most important screen in the system.

**Rules:**
- Show only what will change
- Use before → after
- No prose
- No justification
- No warnings

**Example:**
```
Inventory quantity
12 → 10
```

If you cannot express the change as a diff, the action is invalid.

### Stage 3 — Sign (consent)

**Visual rules:**
- UI dims
- Preview remains visible
- Signature prompt is dominant
- No other actions visible

This is not "confirm".
This is ownership.

### Stage 4 — Commit (write)

**System response:**
```
Updating inventory…
```

- No celebration
- No checkmarks
- No success toast

### Stage 5 — Record (immutable)

After commit, the card shows:
```
Updated by Alex
12 Jan 2026 · 14:32
```

- This is append-only
- Never editable
- Never hidden

---

## 8. Cancellation Rules (safety guarantee)

At every mutation stage:
- Cancel is visible
- Cancel is immediate
- Cancel leaves no residue

If a user cancels:
- Nothing is written
- No logs created
- No side effects

---

## 9. Uncertainty Presentation (first-class)

Uncertainty is shown as parallel options, not errors.

### Visual rules
- Equal visual weight
- Ordered by confidence
- No recommendation copy

### Example:
```
Which did you mean?

• Inventory: Box 2D
• Location: Deck Locker 2D
```

Once selected:
- The rest disappear
- No "you chose" messaging

---

## 10. Status Lines (system transparency)

Status lines:
- Appear inline
- Are factual
- Use present tense
- Auto-dismiss when complete

**Good:**
```
Loading fault history…
```

**Bad:**
```
Working on it for you :)
```

No personality.
No reassurance language.

---

## 11. Visual Tokens Summary (engineer cheat sheet)

| Token | Meaning | Style |
|-------|---------|-------|
| Plain text action | READ | Normal weight |
| Dropdown ▼ | Additional options | Neutral |
| Divider | Semantic separation | Hairline |
| Diff | Mutation preview | Monospace or aligned |
| Dim background | Commitment | Strong |
| Signature prompt | Consent | Dominant |
| Status line | Transparency | Subtle |

---

## 12. What engineers must NOT add (explicit ban list)

- Tooltips
- Info icons
- "Why this action exists"
- Empty-state illustrations
- Success animations
- Gamification
- Chat bubbles
- AI avatars
- Confidence scores shown as percentages
- Auto-executed actions

If it feels friendly, clever, or impressive — it's wrong.

---

## 13. How to judge correctness (litmus tests)

Ask these questions during review:

1. Can I predict exactly what will happen before clicking?
2. Can I cancel safely at any moment?
3. Is responsibility always explicit?
4. Is uncertainty visible rather than hidden?
5. Does the UI stay calm even during failure?

If any answer is "no", the implementation is wrong.

---

## 14. Final instruction (verbatim)

You are not designing a UI.
You are implementing a trust contract.

Every pixel must answer:
"Does this increase clarity, safety, or accountability?"

If it does not, remove it.
