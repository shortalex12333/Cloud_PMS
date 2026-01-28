# Data Classification & Redaction Rules (Required for “classified” claims)

## Classification levels (example)
- HIGHLY CLASSIFIED:
  - documents/manuals/handover notes
  - incident and security reports
  - operational logs that reveal vulnerabilities
- CONFIDENTIAL:
  - crew personal identifiers (limited)
  - role assignments and audit metadata
- INTERNAL:
  - system metrics
  - non-sensitive configuration metadata

## Role-based redaction policy (example)
- crew:
  - see titles/metadata only, no content snippets for classified docs
- HOD:
  - limited snippets (length-capped) where necessary
- manager/captain:
  - full preview where permitted

## Logging policy
- Never log document contents.
- For search queries: log hash + length, not raw string.
- Never log secrets/tokens.

## Streaming policy
- Phase 1: counts only
- Phase 2: role-aware details
