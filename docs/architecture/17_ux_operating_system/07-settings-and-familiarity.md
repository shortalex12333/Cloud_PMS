# CelesteOS — Settings, Familiarity, and Controlled Exposure

## Why This Document Exists

Settings are necessary — but dangerous.

Every system that drifts does so by quietly expanding Settings until it becomes:
- a second control panel
- a hiding place for complexity
- a substitute for clear UX decisions

This document exists to **contain** Settings permanently.

---

## The Role of Settings in Celeste

Settings exist to provide:
- personal orientation
- identity confirmation
- integration management
- security control
- a familiar anchor for new users

Settings do **not** exist to:
- manage work
- control operations
- configure workflows
- compensate for missing UX

---

## Core Principle

> **Settings are a catalog, not a workspace.**

Users should visit Settings rarely.
When they do, they should leave quickly.

---

## What Belongs in Settings (Hard Cap)

Settings may contain only:

### Identity
- Name
- Role
- Department
- Vessel

### Integrations
- Email (Outlook, etc.)
- External services explicitly connected by the user

### Security
- Signing method
- Authentication
- Session management

### Appearance
- Theme
- Display preferences (non-functional)

### Support
- Report issue
- Contact support
- View system notices

### Exit
- Log out

Nothing else.

If a feature proposal does not fit cleanly into one of these categories, it is rejected.

---

## What Must Never Enter Settings

Settings must never contain:
- operational data
- records
- logs
- handovers
- task configuration
- permissions beyond role assignment
- system logic toggles

Settings are not a solution to UX uncertainty.

---

## Access Model

Settings must be:
- reachable via a single secondary affordance
- reachable via search (e.g. “connect outlook”)

Settings must not:
- be the default landing view
- compete visually with search
- contain nested navigation trees

---

## Familiarity Without Betrayal

Settings provide familiarity for users transitioning from legacy systems.

This familiarity is **intentional but limited**.

Settings exist to reassure:
> “I can find my profile, integrations, and security.”

They must never teach users:
> “This is where work happens.”

---

## Transparency and Power

Only users with appropriate roles may see:
- vessel-wide settings
- administrative configuration

All other users see:
- personal settings only

Settings visibility reflects responsibility, not privilege.

---

## Reporting Issues (Required)

A visible “Report issue” entry is mandatory.

Legacy systems fail silently because users exit instead of escalating.

Celeste must:
- make reporting easy
- preserve context automatically
- treat reports as first-class input

---

## Failure Modes (Automatic Rejection)

Any change that:
- adds operational controls to Settings
- introduces configuration sprawl
- hides product weaknesses instead of fixing them
- turns Settings into a control panel

…is rejected.

---

## Success Criteria

Settings are correct if:
- users rarely need them
- users trust that essentials live there
- no one manages work from Settings
- the surface remains static over time

---
# design
Settings shoudl do these thigns;
* show user WHO they are signed in as. and ability to sign out. (Alex, ETO,)
* Their prefernece (light/dark mode)
* Integration (one drive, outlook)
Thats it. 
Anything else is noise. 
---
## Final Lock

> **Settings exist to orient the user, not to extend the system.**

This document is canonical.
