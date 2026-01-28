# Gaps + Decisions to Finalize (So engineering doesn't guess)

These must be decided explicitly, otherwise engineers will improvise.

## Access/membership
- Do we create a dedicated MASTER `memberships` table (recommended)? (Yes/No)
- What are membership statuses and transitions?
- Who can approve privileged roles? (2-person rule for captain/manager?)

## Streaming search
- Minimum prefix length: ?
- Rate limits (user/yacht/IP): ?
- Two-phase streaming: enforce? (recommended)
- What roles can see snippets?

## Caching
- Cache layer: which store (redis/memory)? (document)
- TTL values by endpoint/phase: ?
- Revocation invalidation method: TTL-only or explicit clear?

## Incident mode
- What does global incident mode disable?
- Does it disable signed URLs, streaming, mutations? (recommended: yes)
- How is it triggered and audited?

## Keys
- Do we split service credentials now or later?
- Rotation cadence: ?
