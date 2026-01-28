# Production Readiness Checklist (Hard Gates)

This is the “are we actually safe to onboard more yachts?” list.

## Access control
- [ ] Memberships table exists with explicit status
- [ ] Invite → Accept → Provision flow implemented
- [ ] No manual TENANT edits (policy + technical control)
- [ ] Step-up auth for privileged changes
- [ ] Two-person rule for captain/manager grants (recommended)

## Tenant isolation
- [ ] All tables have yacht_id NOT NULL
- [ ] All handlers validate ownership of referenced IDs
- [ ] RLS policies present for all PMS tables + storage
- [ ] Cache keys include yacht_id + user_id + role

## Streaming search
- [ ] Authz resolves before first streamed byte
- [ ] Server enforces min prefix length
- [ ] Rate limits + concurrency limits enabled
- [ ] Cancellation stops DB work
- [ ] Two-phase streaming implemented (recommended)

## Secrets and service roles
- [ ] No NEXT_PUBLIC secrets
- [ ] Service credentials split by purpose (or documented constraints)
- [ ] Key rotation runbook exists
- [ ] Alerting for unusual privileged actions

## Observability
- [ ] Structured logging with request_id
- [ ] Alerts configured (deny spikes, role changes, streaming flood)
- [ ] Audit logs append-only and retained

## Incident response
- [ ] Tenant kill switch implemented
- [ ] Global incident mode implemented
- [ ] Forensic export path exists
