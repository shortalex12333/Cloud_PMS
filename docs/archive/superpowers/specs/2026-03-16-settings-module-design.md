# Settings Module — Design Spec

**Status:** Approved
**Date:** 2026-03-16
**Prototype:** `.superpowers/brainstorm/6432-1773680335/settings-v4.html`
**Author:** Celeste7

---

## 1. Purpose

A modal settings panel for the Celeste PMS web application. It provides per-user configuration, security transparency, integration management, data control, and SOC-2 compliance affordances. It is **not** a system-administration panel — all org-level settings (NAS path, department, role) are read-only and labelled as administrator-controlled.

---

## 2. Design Principles

| Principle | Rule |
|-----------|------|
| **No ghost features** | Every item in the UI must map to real, working functionality. Non-existent features must not appear, even as disabled placeholders. |
| **Honest content** | Read-only fields are visually distinct (monospace value, "Locked" badge). No fake connection states. |
| **SOC-2 alignment** | Account deletion request, data retention disclosure, and legal document links are required. |
| **Minimal footprint** | Only what a user can actually change or needs to know. No decoration, no upsell, no marketing copy. |
| **Additive styling** | Styles use design tokens only. Zero raw hex values in component CSS. Dark and light modes switch via token replacement. |

---

## 3. Modal Dimensions & Shell

| Property | Value |
|----------|-------|
| Width | 547px |
| Height | 483px |
| Border radius | 8px |
| Overflow | hidden (clips child content) |
| Shadow (dark) | `0 28px 80px rgba(0,0,0,0.80)` + ring |
| Shadow (light) | `0 28px 80px rgba(0,0,0,0.13)` + ring |
| Asymmetric border | Top edge brightest (`rgba(255,255,255,0.13)` dark), bottom and sides dimmer |

The modal is a fixed-size dialog — it does not resize with content. If content overflows, the content area scrolls internally.

### Header

- Height: 42px
- Contents: "Settings" label (left, 12px/600, `--txt2`) + close button (right, 22×22px)
- Background: `rgba(16,14,12,0.65)` with `backdrop-filter: blur(8px)`
- Separated from body by 1px border (`--border-sub`)
- Close button: hover state shows `--surface-hover` background

### Layout

```
┌─────────────────────────────────────────────┐
│  Header (42px)                              │
├──────────────┬──────────────────────────────┤
│  Sidebar     │  Content area                │
│  168px       │  flex: 1                     │
│              │  padding: 20px 18px          │
│              │  overflow-y: auto            │
└──────────────┴──────────────────────────────┘
```

---

## 4. Sidebar

- Width: 168px, fixed (`flex-shrink: 0`)
- Background: `--surface` (one step darker than content)
- Right border: 1px `--border-sub`
- Padding: `8px 6px`

### Navigation Items

Each nav item:
- Height: 32px, padding: `0 9px`
- Gap between items: 1px
- 13×13px icon (left), label (12px, `--txt2`)
- Border radius: 4px
- Left accent border: 2px, transparent by default
- Hover: background `--surface-hover`, label `--txt`
- Active: background `--teal-bg`, label `--txt`, left border `--mark` (brand teal)
- Icon transitions from `--txt3` → `--txt2` on hover/active

### Navigation Items (in order)

| Icon type | Label |
|-----------|-------|
| Person outline | Account |
| Shield | Security |
| 4-grid | Apps |
| Database stack | Data |
| Question circle | Help |
| Info circle | About |

### Sign Out (sidebar footer)

- Pinned below a 1px `--border-sub` separator
- Same nav-item dimensions as above
- Colour: red tint (`rgba(192,80,58,0.72)` dark / `rgba(184,58,40,0.68)` light)
- Hover: `rgba(192,80,58,0.09)` background
- No page content is associated with it — it triggers sign-out action directly

---

## 5. Content Area

- Background: `--surface-el` (slightly elevated)
- Padding: `20px 18px`
- Overflow: `auto` (scrolls independently)
- Page title: 15px / 600 weight / `-0.01em` tracking / `--txt` — provides clear hierarchy above 12.5px row labels
- One page visible at a time; switching is instant (no transition)

### Row Groups

iOS-style shared containers — rows share a single bordered container:

- Background: `--surface`
- Asymmetric border: top brightest, bottom dimmest (matches modal shell pattern)
- Border radius: 5px
- `overflow: hidden` (clips internal row hover to rounded corners)
- Internal dividers: 1px `--border-int` between rows

### Rows

- Min-height: 38px, padding: `9px 12px`
- Label: 12.5px, `--txt2`
- Value: 11px, `--txt3`, right-aligned
- Hover: `--surface-hover` background (60ms transition)
- **Static rows** (read-only): `.no-hover` class — no hover feedback, `cursor: default`
- Rows with a description: two-line left cell (`row-label` + `row-desc` at 11px `--txt3`)

### Typography Rules

| Content type | Font | Class |
|-------------|------|-------|
| Natural language values (role, department, location) | Inter | `.row-value` |
| Structured strings (email, path, timestamp, version) | SF Mono / Fira Code | `.row-value.mono` |

### Section Labels

- 9px / 600 / `letter-spacing: 0.12em` / uppercase / `--txt-ghost`
- Margin-bottom: 5px
- Appear above each row group

### Locked Badge

- "LOCKED" in 9px uppercase
- Background: `rgba(255,255,255,0.05)`, border: `rgba(255,255,255,0.08)`
- Radius: 2px, padding: `1px 5px`
- Displayed inline-right of locked field values

---

## 6. Pages

### Account

**Profile** (read-only group):
| Field | Value source | Editable |
|-------|-------------|----------|
| Email | Auth session | No |
| Department | Org directory | No — "Locked" badge |
| Role | Org directory | No — "Locked" badge |

**Appearance**:
- Theme selector (Dark / Light / System) — dropdown, 25px height

### Security

**Password**:
- "Reset password" row — description: "A reset link will be sent to your email"
- Button: "Send link" (triggers password reset email; no in-app password change)

**Activity** (read-only group):
| Field | Value |
|-------|-------|
| Last sign-in | Formatted date + time (monospace), sourced from auth session |

Location/IP data is **not captured and not stored**. No location row is shown.

No 2FA. No active sessions list. These features do not exist in the system.

### Apps

**Integrations**:
- Microsoft 365 row — description: "Outlook email and calendar" — "Connect" button (primary)
- Additional connected apps rendered here as they are added

**Request an integration**:
- Single row: text input (`placeholder: "e.g. Slack, Jira, Maximo…"`) + "Send" button
- "Send" opens: `mailto:contact@celeste7.ai?subject=integration request from {user_id}&body={encoded_input}`
- Note below group: "Let us know which tools your crew use. Every request is reviewed by the team."

No Google Workspace. No integrations that do not exist.

### Data

**Storage** (read-only):
- NAS path — value in monospace — "Locked" badge — description: "Set by your administrator"

**Your data**:
- "Export activity log" — description: "All reads, writes, and navigation" — "Export" button

**Retention note** (plain text, 11px, `--txt3`):
> "Celeste stores only what's necessary to run the system. Activity logs are retained for 90 days. Attachments follow your vessel's NAS retention policy."

**Account deletion** (danger zone — pinned to bottom of page via `margin-top: auto`):
- Danger-styled container: red tint border, red tint background
- Label: "Request account deletion" (red)
- Description: "Your data will be removed within 30 days" (red, muted)
- Button: "Request" (danger style) — requires confirmation dialog before submission
- **Implementation:** Insert row into Supabase `deletion_requests` table: `{ user_id, requested_at, status: 'pending' }`. No email API required. Internal team queries the table to process requests.
- SOC-2 requirement: this affordance is mandatory for data subject rights

### Help

**Contact support**:
- Textarea: `placeholder: "Describe the issue — what you were doing, what you expected, what happened…"`
- Min-height: 72px, resize: none
- "Send" opens: `mailto:contact@celeste7.ai?subject=feedback from {user_id}&body={encoded_textarea}`
- Focus state: teal border ring

**Resources** (link group):
| Label | Destination |
|-------|-------------|
| Documentation | `https://celeste7.ai/docs` |
| Release notes | `https://celeste7.ai/release-notes` |

Both open in new tab (↗ external link icon, 11×11px SVG).

### About

**Version block** (separated by bottom border):
- "VERSION" label: 9px uppercase ghost
- Version number: 22px / 600 / monospace / `--txt`
- Build date: 11px monospace `--txt3` — format: `Build YYYY.MM.DD · Celeste7 Ltd`

**Legal** (link group):
| Label | Destination |
|-------|-------------|
| Terms of service | `https://celeste7.ai/terms` |
| Privacy policy | `https://celeste7.ai/privacy` |
| Data processing agreement | `https://celeste7.ai/dataterms` |

All three open in new tab. DPA is required for SOC-2 and GDPR B2B compliance.

---

## 7. Buttons

| Variant | Use |
|---------|-----|
| Default | Neutral actions (Send link, Export) |
| Primary | Confirmatory / brand actions (Connect, Send integration request, Send support) |
| Danger | Destructive or compliance-sensitive actions (Request deletion) |

All buttons: 25px height, 11px/500 font, 3px radius, asymmetric border (top brightest).

---

## 8. Design Token Mapping

Both modes use identical component classes. Colour switches entirely through token reassignment on `.light` container.

| Token | Dark | Light |
|-------|------|-------|
| `--surface` | `#181614` | `#FFFFFF` |
| `--surface-el` | `#1e1b18` | `#FDFCFB` |
| `--surface-hover` | `#252525` | `#EDEAE4` |
| `--surface-act` | `#2c2925` | `#E8E3DC` |
| `--txt` | `rgba(255,255,255,0.92)` | `rgba(15,12,9,0.90)` |
| `--txt2` | `rgba(255,255,255,0.55)` | `rgba(15,12,9,0.60)` |
| `--txt3` | `rgba(255,255,255,0.40)` | `rgba(15,12,9,0.46)` |
| `--txt-ghost` | `rgba(255,255,255,0.20)` | `rgba(15,12,9,0.30)` |
| `--mark` | `#5AABCC` | `#2B7BA3` |
| `--teal-bg` | `rgba(58,124,157,0.13)` | `rgba(43,123,163,0.09)` |
| `--red` | `#C0503A` | `#B83A28` |
| `--red-bg` | `rgba(192,80,58,0.10)` | `rgba(184,58,40,0.06)` |
| `--red-border` | `rgba(192,80,58,0.22)` | `rgba(184,58,40,0.20)` |

Asymmetric border pattern (dark):
```
border-top:    1px solid rgba(255,255,255,0.09);  /* catches ambient light */
border-right:  1px solid rgba(255,255,255,0.05);
border-bottom: 1px solid rgba(255,255,255,0.02);  /* fades into dark bg */
border-left:   1px solid rgba(255,255,255,0.05);
```

---

## 9. Interaction Behaviour

| Trigger | Behaviour |
|---------|-----------|
| Nav item click | Instant page swap, nav active state updates, title updates |
| Sign out click | Triggers sign-out flow (implementation-defined) |
| Send link (Security) | Triggers Supabase auth password reset; button shows loading → "Sent" state |
| Connect (Apps) | Initiates OAuth flow for Microsoft 365 |
| Send integration request | `mailto:contact@celeste7.ai?subject=integration request from {user_id}&body={input}` |
| Export (Data) | Downloads activity log as **CSV** |
| Request deletion (Data) | Confirmation dialog → inserts row into Supabase `deletion_requests` table |
| Send (Help) | `mailto:contact@celeste7.ai?subject=feedback from {user_id}&body={textarea}` |
| External links (Help/About) | `target="_blank" rel="noopener noreferrer"` |
| Close button | Closes modal, returns to previous state |
| Esc key | Same as close button |

---

## 10. Accessibility

- All interactive elements require `:focus-visible` ring (teal, 2px, offset 1px) — to be added at implementation
- Static (locked) rows: `cursor: default`, no hover state, no focus ring
- External link icons: `aria-label` or visually hidden text "opens in new tab"
- Modal: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to header title
- Sign out item: not a nav page — should be `<button>` or `role="button"`, not a nav link

---

## 11. Out of Scope

The following were explicitly excluded from this design:

| Feature | Reason |
|---------|--------|
| Two-factor authentication | Does not exist in the system |
| Active sessions list | Does not exist in the system |
| Google Workspace | Does not exist in the system |
| IP geolocation / location display | Not captured, not stored — privacy by default |
| Notification preferences | Deferred — no notification system yet |
| Language / locale | Deferred |
| In-app password change | Security best practice: email reset only |
| Admin panel controls | Separate admin surface, not per-user settings |

---

## 12. Resolved Decisions

All questions resolved prior to implementation planning.

| # | Question | Decision |
|---|----------|----------|
| 1 | Documentation & Release notes URLs | `celeste7.ai/docs`, `celeste7.ai/release-notes` |
| 2 | Legal document URLs | `celeste7.ai/terms`, `celeste7.ai/privacy`, `celeste7.ai/dataterms` |
| 3 | Help form routing | `mailto:contact@celeste7.ai` — subject pre-filled "feedback from {user_id}", body from textarea |
| 4 | Integration request routing | `mailto:contact@celeste7.ai` — subject pre-filled "integration request from {user_id}", body from input |
| 5 | Account deletion backend | Supabase insert into `deletion_requests` table `{ user_id, requested_at, status: 'pending' }` — no email API required |
| 6 | Activity log export format | CSV |
| 7 | IP geolocation / location | Not captured, not stored — location row removed from Security page |
