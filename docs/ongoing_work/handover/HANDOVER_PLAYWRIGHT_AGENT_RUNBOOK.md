# Handover — Playwright Agent Runbook

> **For:** Any Claude Code agent with `mcp__playwright__*` tools available  
> **Purpose:** Operate `app.celeste7.ai` as real users, complete every handover scenario, capture console errors, and populate `HANDOVER_MANUAL_TEST_LOG.md` with real Y/N/ERR results  
> **Output:** The test log file at `docs/ongoing_work/handover/HANDOVER_MANUAL_TEST_LOG.md` filled in with evidence

---

## How this works

1. Agent opens a Playwright browser via MCP
2. Agent injects a console error collector into the page
3. Agent executes each scenario (navigate, click, fill, verify)
4. After each scenario: agent reads collected errors, writes Y/N/ERR into the MD file
5. Agent closes the browser and reopens for the next scenario (clean state per scenario)
6. Agent uses `Edit` tool to populate the MD file row by row

---

## Step 0 — Verify Playwright MCP is available

Before starting, confirm you have these tools:
```
mcp__playwright__browser_navigate
mcp__playwright__browser_click
mcp__playwright__browser_type
mcp__playwright__browser_snapshot
mcp__playwright__browser_screen_capture
mcp__playwright__browser_evaluate
mcp__playwright__browser_close
```

If any are missing, stop. Tell the user: "Playwright MCP not loaded — restart Claude Code session."

---

## Step 1 — Browser setup + console collector injection

After every `browser_navigate`, inject this via `browser_evaluate`:

```javascript
// Console error collector — survives SPA navigation within the same page
window.__handoverErrors = window.__handoverErrors || [];
window.__handoverWarnings = window.__handoverWarnings || [];

const _origError = console.error;
console.error = (...args) => {
  window.__handoverErrors.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
  _origError.apply(console, args);
};

const _origWarn = console.warn;
console.warn = (...args) => {
  window.__handoverWarnings.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
  _origWarn.apply(console, args);
};

// API call interceptor — logs all /v1/ calls with status
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
  if (url.includes('/v1/') || url.includes('/api/') || url.includes('/actions/')) {
    if (!r.ok) {
      window.__handoverErrors.push(`[API ${r.status}] ${url}`);
    }
  }
  return r;
};

'console collector injected';
```

To read collected errors after a scenario:

```javascript
JSON.stringify({
  errors: window.__handoverErrors || [],
  warnings: window.__handoverWarnings || [],
  errorCount: (window.__handoverErrors || []).length,
});
```

---

## Step 2 — Login pattern

Repeat this for each role change. Close browser between roles for clean state.

### Login as crew
```
1. browser_navigate → https://app.celeste7.ai/login
2. browser_click → element: input[name="email"] or input[type="email"]
3. browser_type → text: crew.test@alex-short.com
4. browser_click → element: input[name="password"] or input[type="password"]
5. browser_type → text: Password2!
6. browser_click → element: button[type="submit"] or the "Sign In" / "Log In" button
7. Wait for navigation — browser_snapshot to verify dashboard loaded
8. Inject console collector (Step 1)
```

### Login as captain
Same pattern, email: `captain.tenant@alex-short.com`

### Login as HOD
Same pattern, email: `hod.test@alex-short.com`

---

## Step 3 — Element selector reference

Instead of "click the button in the top right", use these exact selectors.

### Sidebar navigation
```
Handover link:     a[href*="handover-export"] OR text="Handover"
Faults link:       a[href*="faults"] OR text="Faults"
Work Orders link:  a[href*="work-orders"] OR text="Work Orders"
Equipment link:    a[href*="equipment"] OR text="Equipment"
Certificates link: a[href*="certificates"] OR text="Certificates"
```

### Handover page tabs
```
Queue tab:         button:has-text("Queue")
Draft Items tab:   button:has-text("Draft Items")
```

### Queue section headers (click to expand/collapse)
```
Open Faults:              div:has-text("Open Faults") >> nth=0
Overdue Work Orders:      div:has-text("Overdue Work Orders") >> nth=0
Low Stock Parts:          div:has-text("Low Stock Parts") >> nth=0
Pending Purchase Orders:  div:has-text("Pending Purchase Orders") >> nth=0
```

### Queue item buttons
```
+ Add button:    button:has-text("Add"):not(:has-text("Added"))
✓ Added state:   button:has-text("Added")
```

### Draft Items buttons
```
Export Handover:  button:has-text("Export Handover")
+ Add Note:       button:has-text("Add Note")
```

### Edit popup fields
```
Summary textarea:    textarea
Category dropdown:   select >> nth=0  (first select in popup)
Status radio:        div:has-text("On Going"), div:has-text("Not Started"), div:has-text("Requires Parts")
Section dropdown:    select >> nth=1  (second select, only in Add Note)
Save Changes:        button:has-text("Save Changes")
Add to Handover:     button:has-text("Add to Handover")
Cancel:              button:has-text("Cancel")
```

### Delete confirmation
```
Delete trigger:      button:has-text("Delete") (red text in edit popup footer)
Confirm delete:      button:has-text("Delete Note") (red button in confirmation)
```

### Document page
```
Document header:     text="Technical Handover Report"
No content message:  text="No handover content available"
Section headers:     span with uppercase text + item count (e.g., "DECK 4 items")
Entity links:        a:has-text("View Fault") OR a:has-text("View Work Order")
Signature block:     text="Prepared By"
```

### Sign/Countersign buttons
```
Sign Handover:        button:has-text("Sign Handover")
Countersign:          button:has-text("Countersign Handover")
Canvas element:       canvas[width="416"][height="160"]
Clear button:         button:has-text("Clear")
Cancel (modal):       button:has-text("Cancel") (inside the sign modal)
Confirm & Sign:       button:has-text("Confirm")
```

### Toast messages (sonner toasts)
```
Success toast:     [data-sonner-toast] OR div[role="status"]:has-text("updated") 
Error toast:       [data-sonner-toast][data-type="error"]
Any toast text:    li[data-sonner-toast] >> text content
```

### Status pills
```
Pending Review:         text="Pending Review" (amber)
Pending Hod Signature:  text="Pending Hod Signature" (amber)
Complete:               text="Complete" (green)
Draft:                  text="Draft" (neutral)
```

---

## Step 4 — Scenario execution pattern

For each scenario in `HANDOVER_MANUAL_TEST_LOG.md`:

```
1. Close previous browser (if open): browser_close
2. Open fresh browser: browser_navigate to login URL
3. Login as required role (Step 2)
4. Inject console collector (Step 1 evaluate)
5. Execute steps (navigate, click, fill, verify via snapshot)
6. After all steps: read console errors (Step 1 evaluate read)
7. Use Edit tool to populate the MD file:
   - Y if element was found and behaviour matched
   - N if element missing or behaviour wrong
   - ERR if console error appeared during the step
   - Paste relevant console errors in the "Console errors" column
8. Write scenario notes block with any observations
```

### How to verify an element exists (VISUAL PROOF)

```
1. browser_snapshot → get the accessibility tree / DOM snapshot
2. Search the snapshot text for the expected element or text
3. If found → Y
4. If not found → take browser_screen_capture → save screenshot → N with note
```

### How to verify a toast appeared

```
1. After the action (click button), wait 2 seconds
2. browser_snapshot → look for toast text in the DOM
3. Toasts use sonner library — look for [data-sonner-toast] or role="status"
4. If toast text matches expected → Y
5. If no toast → N, check console errors
```

### How to draw on signature canvas

```
1. browser_evaluate:
   const canvas = document.querySelector('canvas');
   if (canvas) {
     const ctx = canvas.getContext('2d');
     ctx.beginPath();
     ctx.lineWidth = 2;
     ctx.strokeStyle = '#1A2332';
     ctx.moveTo(50, 80);
     ctx.lineTo(100, 40);
     ctx.lineTo(150, 90);
     ctx.lineTo(200, 50);
     ctx.lineTo(300, 80);
     ctx.stroke();
     'signature drawn';
   } else {
     'no canvas found';
   }
```

Then click "Confirm & Sign" button.

---

## Step 5 — MD file population pattern

After each scenario, use the `Edit` tool to replace table cells.

Example — Scenario 1, step 1.1:
```
Old: | 1.1 | Click **Handover** in sidebar | Sidebar nav, OPERATIONS section | `/handover-export` loads, two tabs visible | | |
New: | 1.1 | Click **Handover** in sidebar | Sidebar nav, OPERATIONS section | `/handover-export` loads, two tabs visible | Y | |
```

If there were console errors:
```
New: | 1.1 | Click **Handover** in sidebar | Sidebar nav, OPERATIONS section | `/handover-export` loads, two tabs visible | ERR | `[API 400] /v1/handover/items` |
```

After all steps in a scenario, populate the notes block:
```
Old: **Notes / errors for Scenario 1:**
\`\`\`

\`\`\`

New: **Notes / errors for Scenario 1:**
\`\`\`
1.1 — Y. Page loaded in 1.2s, both tabs visible.
1.4 — Y. Open Faults shows 0 items (expandable, correct).
1.6 — Y. Low Stock Parts shows 20 items with stock levels.
Console: 1 warning — CSS preload not used (non-blocking).
\`\`\`
```

---

## Step 6 — Browser reset between scenarios

```
1. browser_close (kills current browser instance)
2. For next scenario: browser_navigate to login URL (opens fresh browser)
3. This ensures:
   - No session bleed between roles
   - No stale console errors from previous scenario
   - Clean localStorage/sessionStorage
   - Fresh Supabase auth state
```

---

## Step 7 — Final summary

After all scenarios are complete:

1. Read the full MD file
2. Count Y/N/ERR across all scenarios
3. Populate the "Overall verdict" table at the bottom
4. Populate "All console errors" section with unique errors
5. Commit the populated file:
   ```
   git add docs/ongoing_work/handover/HANDOVER_MANUAL_TEST_LOG.md
   git commit -m "test(handover): populated manual test log — N/M passed, K errors"
   ```

---

## Quick-start prompt for the agent

Copy this prompt to kick off the testing agent:

```
You are HANDOVER_TESTER. Your job is to test the handover domain on app.celeste7.ai
using Playwright MCP browser tools. You must:

1. Read the runbook at docs/ongoing_work/handover/HANDOVER_PLAYWRIGHT_AGENT_RUNBOOK.md
2. Read the test log at docs/ongoing_work/handover/HANDOVER_MANUAL_TEST_LOG.md
3. For each scenario (1-12):
   a. Open a fresh browser (close previous one first)
   b. Login as the specified role
   c. Inject the console collector
   d. Execute each step using browser_navigate, browser_click, browser_type, browser_evaluate
   e. Verify results using browser_snapshot
   f. Read console errors via browser_evaluate
   g. Edit the MD file to fill in Y/N/ERR for each step
   h. Write observations in the notes block
4. After all scenarios: fill in the Overall verdict table
5. Commit the populated test log

Credentials:
- crew: crew.test@alex-short.com / Password2!
- HOD: hod.test@alex-short.com / Password2!
- captain: captain.tenant@alex-short.com / Password2!

Start with Scenario 1 (Pre-flight + Queue loads). Go.
```

---

## Known Playwright MCP limitations

| Limitation | Workaround |
|-----------|-----------|
| Canvas drawing (mouse events) | Use `browser_evaluate` to draw programmatically on the canvas context |
| Toast detection timing | Take snapshot 2s after action; toasts auto-dismiss after 4s |
| SPA navigation (no full reload) | Re-inject console collector after `browser_navigate` if page changes |
| File upload | Not possible via MCP — skip upload scenarios |
| Print dialog (`window.print()`) | Cannot verify — mark as "SKIP — browser print dialog not testable via MCP" |
| Mobile viewport | Default is desktop — add `viewport` param if testing mobile |
