# Threat Model (CISO-Grade) — Mapped to Your Controls

This threat model is intentionally structured for SOC 2 / ISO evidence.

## Assets
- Classified yacht PMS records (TENANT)
- Classified documents (TENANT storage)
- Membership mapping and status (MASTER)
- Secrets and service role keys (env)
- Audit logs (MASTER/TENANT)

## Threat actors
- External attacker (credential theft, token replay, enumeration)
- Malicious insider (Celeste staff or contractor)
- Compromised device (agent machine)
- Compromised service (Render, CI, dependency, leaked env)
- Customer misconfiguration (wrong invite, wrong role)

## STRIDE analysis (practical)

### Spoofing
Threats:
- Use stolen JWT to access yacht data
- Device impersonation
Controls:
- JWT verification using MASTER secret
- Membership status gating (MASTER)
- Role gating (TENANT)
- Device enrollment tokens, device ID, and revocation
Residual risk:
- Token theft between issuance and expiry
Mitigations:
- Short-lived access tokens, refresh tokens on server
- Device-bound tokens and key rotation

### Tampering
Threats:
- Cross-yacht writes by bug or malicious request
- Role escalation via malformed payload
Controls:
- Handler-level yacht_id injection + strict validators
- Ownership checks for all IDs in payload
- RLS policies as backstop
- Signed actions for sensitive operations
Residual risk:
- Service role bypass if validators missing
Mitigations:
- Centralized validator library + deny-by-default
- CI tests for cross-yacht writes with random IDs
- Structured action registry requiring explicit authorization definitions

### Repudiation
Threats:
- User denies approving change
Controls:
- Append-only audit logs with actor, role, yacht_id, timestamp, payload hash
Mitigations:
- Step-up auth for signed actions
- External log shipping (roadmap)

### Information disclosure (highest severity)
Threats:
- Cross-tenant read via bug or misconfigured RLS
- Storage path traversal
- Cache key collision or shared cache leakage
- Streaming search metadata leaks
Controls:
- Membership status gating (MASTER)
- Role-based gating (TENANT)
- yacht_id filtering and RLS
- Storage policies using yacht_id path prefix
- Cache keys must include yacht_id + user_id + role
- Streaming safeguards (see streaming doc)
Mitigations:
- Isolation tests for cache + streaming + storage
- Dedicated tenant DB option for highest-risk yachts
- Tenant-scoped encryption keys (roadmap)

### Denial of service
Threats:
- Search as you type floods backend
- Vector queries heavy
Controls:
- Rate limiting (per IP + per user + per yacht)
- Debounce on client, min prefix length on server
- Query budgets/timeouts
- Circuit breakers and load shedding
Mitigations:
- Per-tenant quotas + “degraded mode”
- Async indexing pipeline

### Elevation of privilege
Threats:
- Crew escalates to manager/captain
- Celeste admin accidentally assigns wrong role
Controls:
- Two-person approval for sensitive roles (recommended)
- Time-bound roles with valid_until
- Step-up authentication for role changes
- Audit + alert on privileged grants
