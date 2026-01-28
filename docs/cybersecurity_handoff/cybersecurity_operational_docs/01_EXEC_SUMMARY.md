# Executive Summary (CISO / Founder / Counsel)

## Current position
You operate a **control-plane / data-plane** split:

- MASTER: Identity, memberships, routing metadata, fleet registry
- TENANT: Yacht-scoped PMS + documents + role bindings mirrored from MASTER
- Render Action Router: Server-only execution boundary, intent validation, audit

This pattern is credible and scalable **if** you tighten the guardrails and remove
all manual production data-plane operations.

## Why this matters (your stated risk)
You described an exposure scenario of **$50m lawsuit per yacht** for a leak.
That requires an architecture where:
- a single bug does not leak data,
- a single employee mistake does not leak data,
- and a single compromised credential does not automatically equal disclosure.

That means **multi-layer enforcement** and **provable controls**.

## Biggest current risks (honest)
1. **Service role bypass risk**: RLS is bypassed by design when using service role.
   If any handler fails to enforce yacht_id scoping + ownership checks, blast radius increases.
2. **Manual provisioning risk**: Any direct DB edits by Celeste staff become a high-risk pathway.
3. **Streaming search amplification**: Search-as-you-type can leak metadata (existence) and can
   hammer backends; without careful gating/caching, it increases attack surface.

## What changes are required before production scale
- Implement an **Access Lifecycle** system (Invite → Accept → Provision → Active → Revoke)
  executed only through Action Router/admin endpoints.
- Centralize **tenant resolution** and forbid client-supplied tenant context.
- Implement **resource ownership validation** for every ID in payloads.
- Add **tenant kill switch** and step-up auth for sensitive actions.
- Expand CI isolation tests to include streaming + caching + negative cases.
- Adopt a clear policy of **no direct TENANT access by humans** in production.

## Success definition
A deployment is “production-grade” only if:
- Cross-yacht read/write attempts fail with 4xx (never 500)
- Role escalation attempts fail with 4xx and trigger alerting
- Revocation takes effect within minutes (cache TTL bounded)
- Streaming endpoints do not begin output until tenant+role resolved
- Audit trail is complete and tamper-resistant within your operational constraints
