---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/HandoverLens.tsx
  - apps/web/src/app/handover/[id]/page.tsx
autonomous: true
requirements: [HAND-03]
---

# Plan FE-03-02: Handover Lens Rebuild

## Objective

Rebuild Handover lens for crew rotation sign-off: LensHeader, VitalSignsRow (status, outgoing crew, incoming crew, items count, export status), sections (Items, Signatures, Exports), dual signature workflow.

## Tasks

<task id="1">
Create HandoverLens.tsx:

VitalSignsRow with 5 signs:
- Status (draft/pending_signatures/complete) - StatusPill
- Outgoing (outgoing crew member name)
- Incoming (incoming crew member name)
- Items ("N items")
- Export ("PDF ready" or "Not exported")
</task>

<task id="2">
Create handover-specific sections:

- **ItemsSection** - Handover items with descriptions, status
- **SignaturesSection** - Outgoing signature, incoming signature (both required)
- **ExportsSection** - Export history, download links

Use HandoverItemsSection and HandoverExportsSection if they exist.
</task>

<task id="3">
Create useHandoverActions hook:

Actions:
- add_handover_item
- edit_handover_item
- validate_handover
- finalize_handover (locks for signatures)
- sign_outgoing (signature required)
- sign_incoming (signature required)
- export_handover

Role-based: crew can add/edit items, finalize requires validation, signatures per role.
</task>

<task id="4">
Implement dual signature flow:

1. Finalize locks the handover
2. Outgoing crew signs first (SignaturePrompt)
3. Incoming crew signs second
4. Both signatures = complete status
5. Can export to PDF after complete
</task>

<task id="5">
Wire handover/[id]/page.tsx and verify build.
</task>

## must_haves

- [ ] HandoverLens.tsx with full-screen layout
- [ ] VitalSignsRow with outgoing/incoming crew names
- [ ] Items section with handover items
- [ ] Dual signature flow (outgoing + incoming)
- [ ] Export to PDF functionality
- [ ] Build passes
