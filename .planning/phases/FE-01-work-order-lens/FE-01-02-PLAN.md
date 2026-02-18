---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/sections/NotesSection.tsx
  - apps/web/src/components/lens/sections/PartsSection.tsx
  - apps/web/src/components/lens/sections/AttachmentsSection.tsx
  - apps/web/src/components/lens/sections/HistorySection.tsx
  - apps/web/src/components/ui/SectionContainer.tsx
autonomous: true
requirements: [WO-03]
---

# Plan FE-01-02: Work Order Section Containers

## Objective

Build all Work Order section containers with sticky headers, adjacent action buttons, and proper empty states: Notes, Parts Used, Attachments, History.

## Tasks

<task id="1">
Create `NotesSection.tsx`:

```tsx
interface NotesSectionProps {
  notes: WorkOrderNote[];
  onAddNote: () => void;
  canAddNote: boolean;
}
```

Structure:
- SectionContainer wrapper with sticky header
- Header: "Notes (N)" with [+ Add Note] button adjacent
- Each note: author, timestamp, content (truncated to 3 lines with expand)
- Empty state: "No notes yet. Add the first note to document progress."
</task>

<task id="2">
Create `PartsSection.tsx`:

```tsx
interface PartsSectionProps {
  parts: WorkOrderPart[];
  onAddPart: () => void;
  canAddPart: boolean;
}
```

Structure:
- SectionContainer with sticky header
- Header: "Parts Used" with [+ Add Part] button
- Each part: part name, quantity, status (consumed/reserved)
- Part name is EntityLink to Parts lens
- Empty state: "No parts used yet."
</task>

<task id="3">
Create `AttachmentsSection.tsx`:

```tsx
interface AttachmentsSectionProps {
  attachments: Attachment[];
  onAddFile: () => void;
  canAddFile: boolean;
}
```

Structure:
- SectionContainer with sticky header
- Header: "Attachments (N)" with [+ Add File] button
- Media files (.png, .jpg, .mp4, .heic): render inline, max-height 240px
- Documents (.pdf, .docx): render as preview card with icon, filename, size
- Document cards are clickable → open Document lens
- Empty state: "No attachments. Add photos or documents."
</task>

<task id="4">
Create `HistorySection.tsx`:

```tsx
interface HistorySectionProps {
  history: AuditLogEntry[];
}
```

Structure:
- SectionContainer with sticky header
- Header: "History" (no action button, read-only)
- Each entry: action, actor, timestamp, details (collapsed by default)
- Most recent first
- Infinite scroll or "Load more" if > 20 entries
- No empty state (work orders always have creation entry)
</task>

<task id="5">
Verify SectionContainer sticky behavior:

1. Scroll the lens content
2. Verify each section header sticks when reaching top
3. Verify background changes to surface-elevated when pinned
4. Verify action buttons remain clickable while pinned
</task>

<task id="6">
Build passes:

```bash
cd apps/web && npm run build
```
</task>

## Verification

```bash
# All section files exist
ls apps/web/src/components/lens/sections/

# Build passes
cd apps/web && npm run build

# Sticky header uses IntersectionObserver
grep -n "IntersectionObserver\|isPinned" apps/web/src/components/ui/SectionContainer.tsx
```

## must_haves

- [ ] NotesSection renders notes with add button
- [ ] PartsSection renders parts with EntityLink
- [ ] AttachmentsSection differentiates media vs documents
- [ ] HistorySection renders ledger entries
- [ ] All headers stick on scroll
- [ ] Empty states are contextual, not generic
- [ ] Build passes
