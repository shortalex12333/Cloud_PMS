# Known Flaws & Mitigations

## Service Role Bypass
Risk:
- Service role can bypass RLS

Mitigation:
- Centralised validators
- Explicit yacht_id enforcement
- CI tests for cross-tenant access
- Role-split service credentials (roadmap)

## Human Error
Risk:
- Manual DB edits

Mitigation:
- No human DB access
- Admin workflows only
- Full audit trails

## Shared DB Risk
Risk:
- Logical isolation failure

Mitigation:
- Multiple enforcement layers
- Dedicated DB tier for high-risk clients
