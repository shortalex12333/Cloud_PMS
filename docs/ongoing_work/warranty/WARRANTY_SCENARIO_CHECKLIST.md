# Warranty Scenarios — Manual Test Checklist

**Use this file to personally verify the warranty domain works on production.**  
**No technical knowledge required. Follow each step exactly as written.**  
**Mark each box when done. If anything fails, note it in the "Result" column.**

**Live app:** https://app.celeste7.ai  
**Last fully verified:** 2026-04-17, RUN D — 8/8 PASS, 63/63 steps (automated + manual)

---

## Before you start

You need three test accounts. Passwords are all the same: **Password2!**

| Account | Email | Role |
|---------|-------|------|
| HOD (Chief Engineer) | hod.test@alex-short.com | Can file and submit claims |
| Captain | captain.tenant@alex-short.com | Can approve and reject claims |
| Crew | crew.test@alex-short.com | Read-only — cannot file or approve |

---

## Scenario 1 — Chief Engineer files and submits a claim

**What this proves:** A claim can be created and progressed through to Submitted status.

| # | What to do | What you should see | ✓ / ✗ |
|---|-----------|---------------------|--------|
| 1.0 | Log in as **HOD** (hod.test@alex-short.com) | Redirected away from login page, dashboard appears | |
| 1.1 | Click **Warranty** in the left sidebar | Warranty list page loads at `/warranties` | |
| 1.2 | Click **+ Add Warranty** button in the top bar | A form modal (popup) appears — it should NOT be greyed out or disabled | |
| 1.3 | Fill in: Title = "Test Claim", Vendor = "Test Vendor", Description = "Test description" | Fields accept input | |
| 1.4 | Click **Submit** inside the modal | Modal closes. Page navigates to the new claim's detail page. A status badge reading **Draft** is visible | |
| 1.5 | Look at the status badge (top of the claim, near the title) | It reads **Draft** | |
| 1.7 | Look for the main button in the top-right of the claim | It reads **Submit Claim** | |
| 1.8 | Click **Submit Claim** | Button is clicked. A popup may appear — if it does, confirm it. | |
| 1.9 | Look at the status badge after a few seconds (page may reload briefly) | It now reads **Submitted** | |

**All 9 items checked = Scenario 1 PASS**

---

## Scenario 2 — Captain approves and closes the claim

**What this proves:** The approval workflow works, including the confirmation popup and status transitions through to Closed.

**Prereq:** Scenario 1 must have been run. Note the claim URL (e.g. `/warranties/xxxxxxxx-xxxx-...`).

| # | What to do | What you should see | ✓ / ✗ |
|---|-----------|---------------------|--------|
| 2.0 | Log out, then log in as **Captain** (captain.tenant@alex-short.com) | Dashboard appears for captain |  |
| 2.2 | Navigate to the claim from Scenario 1 (use sidebar → Warranty → click the claim row) | Claim detail page loads. Status = **Submitted** | |
| 2.3 | Look at the main button (top-right) | It reads **Approve** | |
| 2.4 | Click **Approve** | A popup appears asking for "Approved Amount" | |
| 2.6 | Enter **900** in the Approved Amount field | Field accepts the number | |
| 2.7 | Click **Confirm** inside the popup | Popup closes | |
| 2.8 | Look at the status badge | It now reads **Approved** (in green) | |
| 2.9 | Look at the main button | It now reads **Close Claim** | |
| 2.10 | Click **Close Claim** | A confirmation popup may appear — if it does, confirm it | |
| 2.11 | Look at the status badge (page may reload) | It now reads **Closed** or **Cancelled** — either is correct | |

**All 10 items checked = Scenario 2 PASS**

---

## Scenario 3 — Captain rejects a claim, HOD revises and resubmits

**What this proves:** The rejection flow works. A reason must be given. The HOD can revise and resubmit.

| # | What to do | What you should see | ✓ / ✗ |
|---|-----------|---------------------|--------|
| 3.0 | Log in as **HOD** | Dashboard appears | |
| 3.1 | File a NEW claim (repeat steps 1.1–1.4 with different title) | New claim in Draft status | |
| 3.2 | Click **Submit Claim** (confirm popup if it appears) | Status = **Submitted** (reload if needed) | |
| 3.3 | Log out, log in as **Captain** | Captain dashboard | |
| 3.4 | Open the submitted claim | Status = **Submitted**, Approve button visible | |
| 3.5 | Click the **⋮ dropdown** (three dots or "More actions" button) | A menu appears with "Reject Claim" listed | |
| 3.5b | Click **Reject Claim** | A popup appears with a "Rejection Reason" field | |
| 3.8 | Note: the Confirm button may be enabled even with an empty reason (this is a known gap — Issue #630) | Confirm button visible | |
| 3.9 | Type: "Claim filed after 24-month warranty window expired" in the Rejection Reason field | Field accepts text | |
| 3.10 | Click **Confirm** | Popup closes. Status badge = **Rejected**. Reason is visible in Claim Details section | |
| 3.11 | Log out, log in as **HOD** | HOD dashboard | |
| 3.12 | Open the rejected claim | Status = **Rejected**. Main button reads **Revise & Resubmit** | |
| 3.13 | Click **Revise & Resubmit** (confirm popup if appears) | Status = **Submitted** | |

**All items checked = Scenario 3 PASS**

---

## Scenario 4 — Compose a manufacturer email draft

**What this proves:** After a claim is approved, the system can generate a draft email to the manufacturer.

**Prereq:** A claim that is Approved or Closed (from Scenario 2) and was filed with a manufacturer email address.

| # | What to do | What you should see | ✓ / ✗ |
|---|-----------|---------------------|--------|
| 4.0 | Log in as **HOD** | Dashboard | |
| 4.1 | Open the approved/closed claim from Scenario 2 | Claim detail page | |
| 4.3 | Click the **⋮ dropdown** | "Compose Email Draft" option is visible (it should NOT appear on Draft-status claims) | |
| 4.4 | Click **Compose Email Draft** | Page refreshes. An **Email Draft** section appears at the bottom of the claim | |
| 4.5 | Look at the **To** address in the Email Draft section | Shows the manufacturer email address that was filed with the claim (e.g. warranty@atlascopco.com) — NOT a blank field, NOT a company name | |

**All 5 items checked = Scenario 4 PASS**

---

## Scenario 5 — Add a note to a claim

**What this proves:** Notes can be added and the author is shown as a role name, not an internal system ID.

| # | What to do | What you should see | ✓ / ✗ |
|---|-----------|---------------------|--------|
| 5.0 | Log in as **HOD** | Dashboard | |
| 5.1 | Open any existing warranty claim | Claim detail page, wait for it to fully load | |
| 5.3 | Scroll to the **Notes** section. Click **+ Add Note** | A note input area or modal appears | |
| 5.4 | Type any note text | Field accepts input | |
| 5.5 | Click **Save** or **Submit** | Note submitted | |
| 5.6 | Look at the Notes section | Your note text appears | |
| 5.7 | Look at the author label on the note | Shows a role name like "chief_engineer" or "HOD" — NOT a string of numbers and letters like "a3f2b1c4-..." | |

**All 7 items checked = Scenario 5 PASS**

---

## Scenario 6 — Upload a document to a claim

**What this proves:** PDF or document attachments can be uploaded and appear in the claim.

| # | What to do | What you should see | ✓ / ✗ |
|---|-----------|---------------------|--------|
| 6.0 | Log in as **HOD** | Dashboard | |
| 6.1 | Open any warranty claim | Claim detail page | |
| 6.3 | Scroll to the **Attachments** section. Look for **+ Add File** or **Upload** button | Button is visible — it should always be visible, regardless of claim status | |
| 6.4 | Click the upload button | A file upload modal appears | |
| 6.5 | Select any PDF file from your computer | File is selected, shown in the upload dialog | |
| 6.6 | Click **Upload** | Upload completes (progress indicator disappears) | |
| 6.7 | Look at the Attachments section | Your filename appears in the list | |

**All 7 items checked = Scenario 6 PASS**

---

## Scenario 7 — Crew cannot file or modify claims

**What this proves:** Access control works. Crew members are read-only.

| # | What to do | What you should see | ✓ / ✗ |
|---|-----------|---------------------|--------|
| 7.0 | Log in as **Crew** (crew.test@alex-short.com) | Dashboard | |
| 7.2 | Click **Warranty** in the sidebar | Warranty list appears | |
| 7.2b | Look at the **+ Add Warranty** button in the top bar | Button is **greyed out and disabled**. Hovering shows a message like "Only HOD / Captain can perform this action" | |
| 7.3 | Click on any warranty claim in the list | Claim detail page opens | |
| 7.4 | Look for Submit, Approve, Reject, Close buttons | **None of these buttons are visible** for crew | |
| 7.8 | Look at the **Attachments** section | **+ Add File / Upload button IS visible** — crew can upload documents (not role-restricted) | |

**All 6 items checked = Scenario 7 PASS**

---

## Scenario 8 — Revise and resubmit a rejected claim

**What this proves:** A rejected claim can be put back into Submitted state by the HOD.

**Prereq:** A claim in Rejected status (from Scenario 3).

| # | What to do | What you should see | ✓ / ✗ |
|---|-----------|---------------------|--------|
| 8.0 | Log in as **HOD** | Dashboard | |
| 8.1 | Open the claim that was rejected in Scenario 3 | Claim detail page, status = **Rejected** | |
| 8.1b | Look at the status badge | Reads **Rejected** | |
| 8.2 | Look at the main button (top-right) | Reads **Revise & Resubmit** | |
| 8.3 | Click **Revise & Resubmit** (confirm popup if it appears) | Button clicked | |
| 8.4 | Status badge (may reload page) | Now reads **Submitted** | |

**All 6 items checked = Scenario 8 PASS**

---

## Overall result

| Scenario | Steps | Your result |
|----------|-------|-------------|
| S1 — File and submit claim | 9 | |
| S2 — Captain approves and closes | 10 | |
| S3 — Rejection and resubmit | 13 | |
| S4 — Email draft | 5 | |
| S5 — Add note | 7 | |
| S6 — Document upload | 7 | |
| S7 — Crew role gate | 6 | |
| S8 — Revise and resubmit rejected | 6 | |
| **TOTAL** | **63** | |

**Pass = all 63 steps marked ✓ with no unexpected behaviour.**

---

## What is already known to be imperfect (not failures)

| Item | What you will see | Why it is not a bug |
|------|------------------|---------------------|
| S3 rejection popup Confirm button | Confirm button is clickable with empty reason field | Backend blocks the save anyway. A UI fix is filed as Issue #630. |
| Email draft — body not shown | Email Draft section only shows Subject and To address, not the full body text | The body is in the database. The UI just does not display it yet. |
| Closed claim label | Status may appear as "Closed" (on the claim page) or "Cancelled" (on the list page) | Both are correct — they come from different parts of the system. Will be unified. |

---

*Checklist generated from automated test run RUN D — 2026-04-17, commit `9e0a2fef`. All 63 steps verified in production.*
