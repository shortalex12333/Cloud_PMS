# Roadmap & Future-proofing (Honest)

## What you can credibly claim now
- Control-plane/data-plane split
- Server-mediated access (Action Router)
- yacht_id scoping + RLS as defense in depth
- Auditable actions and role gating
- Streaming search guardrails (once implemented)

## What you should NOT over-claim yet
- “Cryptographic tenant isolation” (unless you build per-yacht keys)
- “Impossible to leak” (never say this)
- “RLS alone prevents all cross-tenant access” (service role exists)

## High-impact roadmap items
1) Access grants with approvals and expirations
2) Service credential split + rotation automation
3) Tenant kill switch + global incident mode
4) Two-phase streaming search
5) Tenant-scoped encryption keys (KMS) for highest-risk data
6) Dedicated tenant DB option for whales / highest classification

## Scalability notes
- Multi-tenant DB is scalable with proper indexing:
  - composite indexes including (yacht_id, created_at), etc.
- Vector search must always include yacht_id filter
- Separate read replicas or dedicated DB tier can be introduced without changing contracts if routing stays in MASTER
