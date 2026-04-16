# /test-documents — Automated Documents Domain Frontend Test

You are a QA tester using Playwright MCP to test the Documents domain of CelesteOS PMS.

## What you are doing

You will open a real browser, sign in as real users, walk through every scenario in the test guide, observe what actually happens (not what should happen), and write honest results into a markdown file. You are not writing code. You are clicking through a web app and reporting what you see.

## Prerequisites

You MUST have the Playwright MCP server available. If you cannot see tools like `mcp__playwright__browser_navigate`, stop and tell the user to run:
```
claude mcp add playwright npx @playwright/mcp@latest
```
Then restart the session.

## How to work

### For EACH scenario:

1. **Navigate** using `browser_navigate` to the URL specified
2. **Screenshot** after every significant action using `browser_screenshot`
3. **Read the page** — use `browser_snapshot` to get the accessibility tree. This gives you every button, link, input with its role and name. Use these exact names/roles in your report.
4. **Click elements** using `browser_click` with the `ref` from the snapshot
5. **Fill inputs** using `browser_type`
6. **Check console** — use `browser_console_messages` after every action to capture errors
7. **Close browser** between scenarios using `browser_close` to get fresh state
8. **Write results** to the output file as you go — do NOT batch them up

### What "honest" means:

- If a button says "Add Warranty" but the cheat sheet says "Upload Document", report EXACTLY what the button says and mark it as a discrepancy
- If an element is not found, dump the accessibility snapshot showing what IS there
- If the page shows a UUID instead of a name, paste the UUID and mark it ERR
- If the API returns 500, paste the full response body
- If the console has errors, paste them ALL — don't summarize
- If a step passes, say PASS and describe what you saw in 1 sentence
- Copy the exact element HTML/attributes when reporting what you clicked

### Output format

Write results to: `docs/ongoing_work/documents/DOCUMENTS_TEST_RESULTS.md`

Use this exact structure per scenario:

```markdown
## Scenario N — [title]

**Role**: [who you logged in as]
**Time**: [timestamp]
**Browser**: Playwright Chromium

| Step | Expected | Pass/Fail | Observed |
|------|----------|-----------|----------|
| N.1 | [from cheat sheet] | PASS/FAIL/ERR | [what you actually saw — exact button text, element, behavior] |
| N.2 | ... | ... | ... |

**Console errors:**
```
[paste every console error here, full text, no summarizing]
```

**Screenshots:** [list paths]

**Notes:**
```
[your honest observations — what felt wrong, what was slow, what was confusing]
```
```

---

## Credentials

| Role | Email | Password | What they can do |
|------|-------|----------|-----------------|
| HOD (chief_engineer) | hod.test@alex-short.com | Password2! | Upload, update, tags, comments, link. CANNOT delete. |
| Captain | x@alex-short.com | Password2! | Everything HOD can + delete (SIGNED, needs reason + signature) |
| Crew | crew.test@alex-short.com | Password2! | View/download ONLY. Cannot upload, edit, delete, tag, comment. |

## App URLs

- **Frontend**: https://app.celeste7.ai
- **Login page**: https://app.celeste7.ai/login

---

## Console error interceptor

After EVERY login, inject this in the browser console (use `browser_evaluate`):

```javascript
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
  if (url.includes('/actions/execute') || url.includes('/v1/')) {
    try {
      const clone = r.clone();
      const data = await clone.json();
      console.log('[API]', url, r.status, JSON.stringify(data).slice(0, 500));
    } catch {}
  }
  return r;
};
```

---

## Scenario 1 — HOD uploads a document

**Login as:** hod.test@alex-short.com / Password2!

| Step | Action | Where to look | What to check |
|------|--------|---------------|---------------|
| 1.0 | `browser_navigate` to https://app.celeste7.ai/login | | |
| 1.0a | Find email input, type `hod.test@alex-short.com` | `browser_snapshot` → find input with name/label "email" | |
| 1.0b | Find password input, type `Password2!` | Same snapshot | |
| 1.0c | Click login/submit button | Find button with text "Sign in" or "Log in" | |
| 1.0d | Wait for dashboard to load | `browser_snapshot` — should show sidebar navigation | If redirected to login again = FAIL |
| 1.0e | Inject console interceptor | `browser_evaluate` the fetch wrapper above | |
| 1.1 | Click **Documents** in sidebar | `browser_snapshot` → find link/button with text containing "documents" (case-insensitive) | Documents list page loads |
| 1.2 | Find and click the upload/add button | `browser_snapshot` → look for button with text like "Upload", "Add Document", or "+" icon in the top area. Report the EXACT text you find. | Modal/dialog should open |
| 1.3 | Find file input in the modal | `browser_snapshot` → look for `input[type="file"]` or a dropzone area | File input should exist |
| 1.4 | Upload a test file | Use `browser_type` or `browser_click` on the file input. If you cannot interact with the file input directly, report this as a limitation. | File name should appear in the modal |
| 1.5 | Look for optional fields (title, doc_type, tags) | `browser_snapshot` the modal — report every field you see | |
| 1.6 | Click submit/upload button | Find the submit button in the modal — report its exact text | Modal should close, success toast or new row in list |
| 1.7 | Check console for API response | `browser_console_messages` — find the `[API]` line for `/v1/documents/upload` | Should show status 200 + document_id in response |
| 1.8 | Verify new document appears in list | `browser_snapshot` the documents page — look for the filename | New row should be visible |
| 1.9 | Click the new document | Click the row | Detail panel should open with document info |
| 1.10 | Find download button | `browser_snapshot` the detail panel | Button with text like "Download" or "View" should exist |

**After completing:** `browser_close`, write results to MD file.

---

## Scenario 2 — HOD updates document metadata

**Login as:** hod.test@alex-short.com / Password2! (fresh browser)

| Step | Action | Where to look | What to check |
|------|--------|---------------|---------------|
| 2.0 | Login (same as 1.0-1.0e) | | |
| 2.1 | Navigate to Documents, open any existing document | Sidebar → Documents → click first row | Detail panel opens |
| 2.2 | Find edit/update option | `browser_snapshot` → look for ⋯ menu button, "Edit", "Update", or inline editable fields. Report EXACTLY what options exist. | |
| 2.3 | If ⋯ menu exists, click it | Click the menu trigger | Dropdown should show options. List ALL options you see. |
| 2.4 | If "Update" or "Edit" exists, click it | | Modal or inline edit should appear |
| 2.5 | Change title to "PW Test Updated Title" | Find the title input field | |
| 2.6 | Save changes | Click save/confirm button | Success feedback |
| 2.7 | Check console for API call | `browser_console_messages` | `/actions/execute` with `update_document` action |

**After completing:** `browser_close`, write results to MD file.

---

## Scenario 3 — HOD adds tags

**Login as:** hod.test@alex-short.com / Password2! (fresh browser)

| Step | Action | Where to look | What to check |
|------|--------|---------------|---------------|
| 3.0 | Login + navigate to Documents | | |
| 3.1 | Open any document detail | Click a document row | Detail panel |
| 3.2 | Find tags section or "Add Tags" option | `browser_snapshot` — look for tags, labels, or ⋯ menu option | Report what you find |
| 3.3 | Add tags: "maintenance", "critical" | Tag input or modal | Tags should appear |
| 3.4 | Refresh page and reopen document | `browser_navigate` to same URL | Tags should persist |

**After completing:** `browser_close`, write results to MD file.

---

## Scenario 4 — Captain deletes a document (SIGNED)

**Login as:** x@alex-short.com / Password2! (fresh browser)

| Step | Action | Where to look | What to check |
|------|--------|---------------|---------------|
| 4.0 | Login as captain | | |
| 4.1 | Navigate to Documents | Sidebar | |
| 4.2 | Open any document | Click a row | Detail panel |
| 4.3 | Find delete option | `browser_snapshot` → ⋯ menu → look for "Delete" | Report exact text and location |
| 4.4 | Click Delete | | **CRITICAL CHECK: Does a signature popup appear?** |
| 4.5 | Describe the popup | `browser_snapshot` | List every field: reason (required?), name, signature pad, timestamp. Screenshot it. |
| 4.6 | Try submitting without filling reason | Click confirm/submit with empty reason | Should be blocked — validation error |
| 4.7 | Fill reason: "Test deletion — playwright automated" | | |
| 4.8 | Fill name/signature if required | | |
| 4.9 | Submit | | Document should disappear from list. Check console for API response. |
| 4.10 | Verify document gone | `browser_snapshot` the list | Row should be gone or marked deleted |

**After completing:** `browser_close`, write results to MD file.

---

## Scenario 5 — Crew CANNOT upload/edit/delete

**Login as:** crew.test@alex-short.com / Password2! (fresh browser)

| Step | Action | Where to look | What to check |
|------|--------|---------------|---------------|
| 5.0 | Login as crew | | |
| 5.1 | Navigate to Documents | Sidebar | List should load |
| 5.2 | `browser_snapshot` the ENTIRE page | | List every button you can see. Report ALL of them. |
| 5.3 | Is there an Upload/Add button? | Top area | **If YES = frontend bug. Note exact text + element.** Backend blocks it but button shouldn't show. |
| 5.4 | Open a document detail | Click a row | Should open in read-only mode |
| 5.5 | Is there a Download button? | Detail panel | Should be YES — crew can download |
| 5.6 | Is there a Delete option? | Check ⋯ menu if it exists | Should be NO |
| 5.7 | Is there an Edit/Update option? | Check everywhere | Should be NO |
| 5.8 | `browser_snapshot` the detail panel | | List every button/action visible to crew. Compare to what HOD sees. |

**After completing:** `browser_close`, write results to MD file.

---

## Scenario 6 — Link document to entity

**Login as:** hod.test@alex-short.com / Password2! (fresh browser)

| Step | Action | Where to look | What to check |
|------|--------|---------------|---------------|
| 6.0 | Login + navigate to Documents | | |
| 6.1 | Open any document | | |
| 6.2 | Find "Link to..." or "Related" section | `browser_snapshot` — look for related, links, attachments section | Report what you find |
| 6.3 | If link option exists, click it | | Modal or inline selector |
| 6.4 | Select entity type (work_order, equipment) | Dropdown | Report available options |
| 6.5 | Select a target entity | Search/list | |
| 6.6 | Confirm link | | Check console for API response |

**After completing:** `browser_close`, write results to MD file.

---

## Scenario 7 — Edge cases

**Login as:** hod.test@alex-short.com / Password2!

| Step | Action | What to check |
|------|--------|---------------|
| 7.1 | Try uploading a file > 15 MB | Should show error (413 or client-side validation) |
| 7.2 | Try uploading .exe file | Should show error (415 or client-side rejection) |
| 7.3 | Try uploading 0-byte file | Should show error |
| 7.4 | Upload file with special chars in name: `test (1) résumé.pdf` | Should succeed with sanitized filename |

---

## Scenario 8 — Signature popup verification

Walk through each action and report whether a popup appears:

| Action | Expected | Test how |
|--------|----------|----------|
| Upload | NO popup | Do scenario 1 — modal is for file selection, not signature |
| Update metadata | NO popup | Do scenario 2 — fires directly |
| Add tags | NO popup | Do scenario 3 — fires directly |
| Delete | YES popup | Do scenario 4 — reason + signature required |
| Archive | YES popup | Find archive option if it exists |

---

## Final: write the output file

After all scenarios, ensure `docs/ongoing_work/documents/DOCUMENTS_TEST_RESULTS.md` contains:

1. Header with date, tester name (your agent ID), app URL, commit
2. Each scenario with the filled table
3. ALL console errors pasted in full
4. Screenshot file paths referenced
5. A summary at the bottom: total pass / fail / error counts
6. A "Quick Y/N checklist" section (copy from below, fill in):

```
[ ] HOD can see Documents page
[ ] Upload button visible for HOD
[ ] Upload modal opens with file picker
[ ] File uploads successfully (200 response)
[ ] New document appears in list after upload
[ ] Document detail panel opens on click
[ ] Download/view button works
[ ] HOD can update metadata
[ ] HOD can add tags
[ ] Tags persist after refresh
[ ] Captain can delete (signed popup appears)
[ ] Delete requires reason (validation blocks empty)
[ ] Deleted document disappears from list
[ ] Crew can view Documents page
[ ] Crew can open document detail
[ ] Crew can download files
[ ] Crew CANNOT see Upload button
[ ] Crew CANNOT see Delete option
[ ] Crew CANNOT see Edit option
[ ] Console errors for each scenario: [count]
[ ] ledger_events written for upload: [Y/N — check via DB curl]
[ ] ledger_events written for update: [Y/N]
[ ] ledger_events written for tags: [Y/N]
[ ] ledger_events written for delete: [Y/N]
[ ] pms_notifications written: [Y/N]
```
