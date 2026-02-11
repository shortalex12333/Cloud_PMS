# CelesteOS Color Token Reference

Quick reference for all Celeste design tokens.

---

## Usage in Code

```tsx
// Tailwind classes
<div className="bg-celeste-black text-celeste-text-primary">
  <button className="bg-celeste-accent hover:bg-celeste-accent-hover">
    Primary Action
  </button>
</div>

// CSS variables (in CSS/styled-components)
.element {
  background: var(--celeste-accent);
  color: var(--celeste-text-primary);
}
```

---

## Foundation Colors

### Backgrounds (Dark Mode - Primary)

| Class | CSS Variable | Hex | Usage |
|-------|--------------|-----|-------|
| `bg-celeste-black` | `--celeste-black` | `#0A0A0A` | Page background |
| `bg-celeste-bg-secondary` | `--celeste-bg-secondary` | `#121212` | Elevated layer 1 |
| `bg-celeste-bg-tertiary` | `--celeste-bg-tertiary` | `#1A1A1A` | Elevated layer 2 |
| `bg-celeste-surface` | `--celeste-surface` | `#111316` | Cards |
| `bg-celeste-panel` | `--celeste-panel` | `#15191C` | Nested panels |
| `bg-celeste-divider` | `--celeste-divider` | `#1E2428` | Separators |

### Backgrounds (Light Mode)

| Class | CSS Variable | Hex | Usage |
|-------|--------------|-----|-------|
| `bg-celeste-white` | `--celeste-white` | `#EFEFF1` | Page background |
| `bg-celeste-bg-primary-light` | `--celeste-bg-primary-light` | `#EFEFF1` | Primary bg |
| `bg-celeste-bg-secondary-light` | `--celeste-bg-secondary-light` | `#E5E5E7` | Secondary bg |
| `bg-celeste-surface-light` | `--celeste-surface-light` | `#FFFFFF` | Cards |
| `bg-celeste-panel-light` | `--celeste-panel-light` | `#F6F7F8` | Panels |

---

## Text Colors

| Class | CSS Variable | Hex | Usage |
|-------|--------------|-----|-------|
| `text-celeste-text-title` | `--celeste-text-title` | `#EFEFF1` | Titles, headers |
| `text-celeste-text-primary` | `--celeste-text-primary` | `#DADDE0` | Body text |
| `text-celeste-text-secondary` | `--celeste-text-secondary` | `#8A9196` | Secondary info |
| `text-celeste-text-muted` | `--celeste-text-muted` | `#6A6E72` | Hints, tertiary |
| `text-celeste-text-disabled` | `--celeste-text-disabled` | `#4A4E52` | Disabled |

---

## Accent Colors (Use Sparingly)

| Class | CSS Variable | Value | Usage |
|-------|--------------|-------|-------|
| `bg-celeste-accent` | `--celeste-accent` | `#3A7C9D` | Primary buttons |
| `hover:bg-celeste-accent-hover` | `--celeste-accent-hover` | `#327189` | Button hover |
| `ring-celeste-accent-muted` | `--celeste-accent-muted` | `rgba(58,124,157,0.7)` | Focus rings |
| `bg-celeste-accent-subtle` | `--celeste-accent-subtle` | `rgba(58,124,157,0.2)` | Selected bg |
| `border-celeste-accent-line` | `--celeste-accent-line` | `rgba(58,124,157,0.1)` | Dividers |

### When to Use Accent

✅ **YES:**
- Primary action buttons
- Selected/active states
- Focus indicators
- Verified/confirmed states
- Live system indicators

❌ **NO:**
- Decorative icons
- Informational text
- Secondary buttons
- Casual hover states
- Links in body text

---

## Restricted Functional Colors

Use ONLY for their designated semantic purpose.

| Class | Hex | Semantic Usage |
|-------|-----|----------------|
| `text-restricted-red` | `#9D3A3A` | Faults, errors, destructive |
| `bg-restricted-red/10` | — | Error backgrounds |
| `text-restricted-orange` | `#9D6B3A` | Warnings, inspections |
| `text-restricted-yellow` | `#9D8A3A` | Time-sensitive, pending |
| `text-restricted-green` | `#3A9D5C` | Confirmed, completed |

---

## Border Colors

| Class | CSS Variable | Value |
|-------|--------------|-------|
| `border-celeste-border` | `--celeste-border` | `#2A2A2A` |
| `border-celeste-border-subtle` | `--celeste-border-subtle` | `rgba(255,255,255,0.06)` |

---

## Common Patterns

### Primary Button
```tsx
<button className="bg-celeste-accent hover:bg-celeste-accent-hover text-white">
  Submit
</button>
```

### Selected State
```tsx
<div className={cn(
  isSelected
    ? "bg-celeste-accent-subtle border-celeste-accent text-celeste-accent"
    : "bg-celeste-bg-tertiary border-celeste-border text-celeste-text-primary"
)}>
```

### Focus Ring
```tsx
<input className="focus:ring-2 focus:ring-celeste-accent-muted focus:border-celeste-accent" />
```

### Status Badge
```tsx
// Error/Fault
<span className="bg-restricted-red/10 text-restricted-red border-restricted-red/30">
  Fault
</span>

// Success/Complete
<span className="bg-restricted-green/10 text-restricted-green border-restricted-green/30">
  Complete
</span>

// In Progress (uses accent)
<span className="bg-celeste-accent-subtle text-celeste-accent border-celeste-accent-line">
  In Progress
</span>
```

### Card
```tsx
<div className="bg-celeste-surface border border-celeste-border rounded-lg">
  <h3 className="text-celeste-text-title">Title</h3>
  <p className="text-celeste-text-secondary">Description</p>
</div>
```

---

## Migration Cheat Sheet

| Old (Don't Use) | New (Use This) |
|-----------------|----------------|
| `gray-900` | `celeste-black` |
| `gray-800` | `celeste-bg-tertiary` |
| `gray-700` | `celeste-text-secondary` |
| `gray-600` | `celeste-text-secondary` |
| `gray-500` | `celeste-text-disabled` |
| `gray-400` | `celeste-text-muted` |
| `gray-300` | `celeste-border` |
| `gray-200` | `celeste-border` |
| `gray-100` | `celeste-bg-secondary` |
| `gray-50` | `celeste-bg-primary` |
| `blue-600` | `celeste-accent` |
| `blue-500` | `celeste-accent` |
| `blue-400` | `celeste-accent` |
| `#0a84ff` | `celeste-accent` |
| `red-600` | `restricted-red` |
| `green-600` | `restricted-green` |
| `yellow-600` | `restricted-yellow` |
