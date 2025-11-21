⭐ CELESTEOS REQUEST → PURPOSE → OUTPUT MAP

(the complete surface-level micro-action behaviour spec)

This is the universal foundation for your OS.

1. FAULTS / BREAKDOWNS / ALARMS
Typical User Prompts

“Gen 2 SPN 4364 FMI 2”

“Port stabiliser is rumbling”

“CAT 3512 overheating”

“HVAC low pressure on deck 3”

“We have an alarm again — same as yesterday”

WHY they want it

Understand what’s wrong.

See possible causes.

Know severity.

Check if it happened before.

Know what to do next.

Prepare for a WO or handover.

WHAT they want (output)

A Fault Card summarising the issue.

The relevant manual snippet.

History of similar events.

Parts commonly involved.

Clear options (buttons):

“Create Work Order”

“Add to Handover”

“View Manual”

“View History”

“Order Parts”

2. WORK ORDERS / PMS TASKS
Typical Prompts

“What’s due today?”

“Show me overdue tasks.”

“Create work order for generator service.”

“Mark the chiller task done.”

“Add note to the stabiliser task.”

WHY they want it

Track maintenance workload.

Know what needs doing now.

Fix overdue tasks.

Add findings/evidence.

Close tasks.

WHAT they want (output)

A task list filtered by the intent (today, this week, overdue).

A minimal card for each WO with quick buttons:

“Mark Done”

“Add Note”

“Add Photo”

“View History”

“Open Manual”

For creation:

A short, pre-filled draft WO with title + equipment automatically inferred.

3. EQUIPMENT INFORMATION
Typical Prompts

“Show me the watermaker.”

“Everything about CAT 3512.”

“Chiller unit details.”

“What’s the history on stabiliser B?”

WHY they want it

Orientation.

Understand system layout.

See linked faults.

Review maintenance history.

Prep for upcoming work.

WHAT they want (output)

A Equipment Card containing:

Basic info (model, serial, location)

Recent WO

Common faults

Parts associated

Manual access

History timeline

Micro-buttons:

“Open Manual”

“View History”

“Create WO”

“Add to Handover”

4. INVENTORY / SPARE PARTS
Typical Prompts

“Do we have racor 2020 filters?”

“Where is the CAT oil seal stored?”

“Order more impellers.”

“What parts are linked to this generator?”

WHY they want it

Ensure they have the needed spare.

Know where it’s physically located.

Reorder parts before they run out.

Link parts to WOs or faults.

WHAT they want (output)

A Part Card:

Stock level

Storage location

Linked equipment

Recent usage

Last supplier

Micro-buttons:

“Order Part”

“Add to WO”

“Add to Handover”

“View Storage Location”

5. HANDOVER / NOTES / REPORTING
Typical Prompts

“Add this to handover.”

“Summarise this week.”

“Update the stabiliser section.”

“Create handover for next crew.”

WHY they want it

Preserve tribal knowledge.

Communicate status clearly.

Document issues.

Prepare for crew rotation.

WHAT they want (output)

A Handover Card:

Sections (Engineering, AV/IT, Deck, etc.)

Items grouped by system

Faults, WOs, notes pre-populated

Micro-buttons:

“Edit Section”

“Export PDF”

“Add This Item”

“Regenerate Summary”

6. HOURS OF REST / COMPLIANCE
Typical Prompts

“Hours of rest.”

“Update my hours of rest.”

“Did I miss any days?”

“Export last month.”

WHY they want it

Log entries.

Fix missing items.

Check compliance.

Provide evidence for audits.

WHAT they want (output)

Read-only table for vague queries.

Editable table for “update” queries.

Export button when asked for email/PDF.

Compliance highlights (green OK, yellow warning).

7. DOCUMENTS / MANUALS / SOPs
Typical Prompts

“MTU 4000 coolant temp sensor manual.”

“Open stabiliser SOP.”

“Find the fuel transfer procedure.”

“Show me the latest MTU bulletin.”

WHY they want it

Instructions for tasks.

Steps for repairs.

Reference for fault troubleshooting.

Compliance procedures.

WHAT they want (output)

Document Card:

Title

Short preview snippet

Buttons:

“Open Document”

“Related Faults”

“Add to WO”

“Add to Handover”

If the user gave a fault → show relevant section immediately.

8. PURCHASES / SUPPLIERS
Typical Prompts

“Order 2 filters.”

“Show me MTU invoices.”

“Track delivery for the chiller part.”

“Create a PO for stabiliser seals.”

WHY they want it

Replenish inventory.

Track supplier relationships.

Manage delivery timing.

WHAT they want (output)

A Purchase Card:

Items in the request

Supplier

Status

Delivery ETA

Micro-buttons:

“Approve”

“Add Item”

“Upload Invoice”

“Track Delivery”

9. VOYAGE / PORT / OPERATIONAL CHECKS
Typical Prompts

“Arrival checklist.”

“Departure tasks.”

“Fuel transfer log.”

“Pre-guest checklist.”

WHY they want it

Keep operations safe and consistent.

Follow procedures.

Log critical actions.

WHAT they want (output)

A Checklist Card:

Items (tickable)

Status

Notes

Timestamp

Micro-buttons:

“Mark Complete”

“Add Note”

“Add Photo”

10. SHIPYARD / REFIT WORK
Typical Prompts

“Shipyard worklist.”

“Contractor tasks.”

“All open snags for refit.”

“Survey prep.”

WHY they want it

Manage complex multi-team work.

Track contractor progress.

Prepare for surveys.

WHAT they want (output)

A Worklist Card:

Items grouped by system

Tags: contractor, class, urgent

Micro-buttons:

“Add Task”

“Update Progress”

“Export Worklist”

“Tag for Survey”

11. FLEET / MANAGEMENT (if user asks)
Typical Prompts

“Show fleet overdue tasks.”

“All certificates expiring this month.”

“Fleet risk overview.”

WHY they want it

Oversight

Cross-yacht comparison

Compliance management

WHAT they want (output)

A Fleet Summary Card:

List of vessels

Overdue counts

Certificate statuses

Risk indicators

Buttons:

“Open Vessel”

“Export Summary”

12. GENERAL QUERIES (the “conversational” layer of the OS)
Typical Prompts

“What changed on stabiliser B this week?”

“Has gen 1 had this fault before?”

“Anything I should know before we leave port?”

“What's the status of engineering today?”

WHY they want it

Fast situational awareness.

Context without digging.

Snapshot of important items.

WHAT they want (output)

A Smart Summary Card containing:

Recent changes

New faults

Critical tasks

Overdue items

Recommendations

(Like a daily briefing.)

⭐ WHAT THIS DOCUMENT ACHIEVES

This .md provides:

the purpose behind each request

the correct output shape

the UX behavior per request type

the user journey motivations

a clean foundation for your engineer to wire micro-actions to UI components

Nothing here references:

schema

backend

entity extraction

regex

internal routing

It’s purely product-level instructions:
When a user asks X, they should see Y.