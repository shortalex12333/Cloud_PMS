foundations_of_microactions.md

⭐ THE SURFACE-LEVEL FOUNDATION OF MICRO-ACTIONS

(What they do, why they exist, how they behave, no schemas, no backend)

A micro-action is:

A single, atomic operation that moves the user from “intent” → “progress” with no navigation.

It is the smallest possible unit of useful engineering action.

Micro-actions replace:

menus

forms

pages

modules

multi-step workflows

They work exactly like the muscles of the OS — each one moves something.

⭐ THE 7 PURPOSE CLUSTERS → THEIR MICRO-ACTIONS

This is the simplified, foundational mapping.

No tech. Just conceptual purpose:

1. FIX SOMETHING

When something breaks, alarms, vibrates, overheats, leaks, or glitches.

Micro-actions here exist to:

Understand what is happening

Pull relevant context

Present immediate next steps

Reduce cognitive load

Start resolution

Pure actions:

Diagnose

Show manual

Show history

Suggest likely parts

Turn fault → work order

Add note

Add to handover

Show related docs

Behaviour across environments:

At sea: minimal friction, urgency bias

Shipyard: deep context, multi-step reasoning

Guest trip: silent mode, quick clarity

Port: balanced mode

Night shift: low interaction, fast answers

2. DO MAINTENANCE

Regular work, scheduled tasks, daily routines.

Micro-action purpose:

Know what to do now

Know what’s next

Mark progress

Capture evidence

Move tasks forward

Pure actions:

Create task

Show tasks due

Mark done

Add note/photo

Add part

Show checklist

Show manual section

Scenario behaviour:

At sea: only safe tasks surfaced

At anchor: backlog mode

Shipyard: contractor-heavy

Guest mode: minimal disturbance

3. UNDERSTAND EQUIPMENT

What is this system? What’s its state? What does it depend on?

Purpose:

Build mental models instantly

Remove uncertainty

Provide rich context quickly

Pure actions:

Show everything about this equipment

Show history

Show parts

Show linked faults

Show manuals

Predict upcoming failures

Scenario behaviour:

New crew: orientation bias

Chief: high-level view

Audit: evidence-first view

Shipyard: dependency view

4. HANDLE PARTS & INVENTORY

Does the part exist? Should we order more? What does it fit?

Purpose:

Avoid shortages

Support repairs

Track consumption

Keep costs predictable

Pure actions:

Check stock

Order part

Add part to work

Add part to handover

Show storage location

Scan barcode

Scenario variation:

At sea: “do we have it?”

Port: “restock now”

Shipyard: bulk orders

Guest trip: emergency spare checks

5. COMMUNICATE STATUS

Notes, logs, handovers, summaries, reports.

Purpose:

Transfer knowledge

Create continuity

Reduce drift

Record decisions

Pure actions:

Add to handover

Add note

Edit handover section

Export summary

Attach document

Add predictive insight

Scenarios:

Crew change: heavy handover

Weekly: summaries

Breakdown: quick notes

Management: formal updates

Shipyard: daily contractor updates

6. COMPLY WITH RULES

Hours of rest, certificates, logs, audits.

Purpose:

Stay compliant

Avoid violations

Produce evidence

Pure actions:

Log hours

View hours

Show certificate

Show expiry

Export logs

Generate audit prep

Scenarios:

Audit week: heavy checking

Normal season: minimal touch

Shipyard: certificate-heavy

Night shift: fast HOR input

7. GET/BUY THINGS

Suppliers, purchasing, deliveries.

Purpose:

Acquire materials

Track orders

Maintain cost control

Pure actions:

Create purchase

Link supplier

Upload invoice

Track delivery

Approve purchase

Scenarios:

Shipyard: high-volume purchasing

Port: just-in-time ordering

Season: low frequency

Breakdown: emergency boilerplate ordering

⭐ META-FOUNDATION

(What micro-actions fundamentally ARE in the OS)

Every micro-action satisfies one or more of these core operational needs:

1. Resolve uncertainty

(e.g., diagnose, show manual, show history)

2. Advance work

(e.g., create task, close task, add part)

3. Transfer information

(e.g., note, handover, summary)

4. Maintain continuity

(e.g., link docs, attach evidence)

5. Protect compliance

(e.g., log HOR, show expiry)

These 5 principles are the “physics” behind all micro-actions.
Nothing should exist outside these.

⭐ HOW INTENT CHANGES THE MICRO-ACTION

Your vision:
User asks conversationally.
Not “search manual”.
But:

“CAT 3512 overheating, what's the latest state?"

“Gen 2 isn’t happy again, same alarm as yesterday.”

“Chiller sounds rough on startup, what changed?”

“Deck 1 AC low pressure again, history?”

In this paradigm:

1. The intent becomes multi-dimensional.

One sentence contains:

fault

equipment

symptom

time

urgency

environment

risk

implied action

2. The system reduces it to pure micro-actions.

Example sentence:

“CAT 3512 overheating, what’s the latest state?”

→ The OS internally turns into:

diagnose_fault

show_equipment_state

show_manual_section

show_recent_history

suggest_parts

offer_create_work_order

offer_add_to_handover

3. Each micro-action is atomic

…but the user sees it as ONE continuous response.

4. The “spider graph” you mentioned is REAL

It’s:

nodes: equipment, faults, symptoms, parts, docs, people, history

edges: relationships

weight: relevance

context: environment

The conversation becomes graph-activated.

5. Micro-actions are the “leaves” of that graph

They are the endpoints — the output of inference.