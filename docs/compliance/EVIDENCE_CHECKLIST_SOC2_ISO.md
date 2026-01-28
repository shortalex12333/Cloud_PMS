# Evidence Checklist: SOC2 + ISO 27001 Control Mapping

## Purpose
This document maps CelesteOS security controls to SOC2 Trust Service Criteria and ISO 27001 Annex A controls. Use this checklist during audits to locate evidence artifacts.

---

## SOC2 CC6 — Logical and Physical Access Controls

### CC6.1 — Logical Access Security
**Control**: The entity restricts logical access to information assets using access control software and rule sets.

| Evidence Type | Artifact Location | Retention | Notes |
|--------------|-------------------|-----------|-------|
| Membership records | `memberships` table (MASTER DB) | 7 years | INVITED → ACCEPTED → ACTIVE → REVOKED |
| Role assignments | `auth_users_roles` table (TENANT DB) | 7 years | yacht_id scoped |
| Access approvals | `security_events` table, type=`admin_approve_*` | 7 years | Includes inviter_id + approver_id |
| Privileged role grants | 2-person approval audit trail | 7 years | captain/manager/chief_engineer require different approver |

**Export Command**:
```bash
python scripts/compliance/export_audit_evidence.py \
  --yacht-id <YACHT_ID> \
  --start 2026-01-01T00:00:00Z \
  --end 2026-03-31T23:59:59Z \
  --out evidence/Q1-2026
```

### CC6.2 — Access Provisioning
**Control**: The entity creates, modifies, or removes access to data, software, functions, and other protected assets based on authorized requests.

| Evidence Type | Artifact Location | Retention | Notes |
|--------------|-------------------|-----------|-------|
| Invite requests | `memberships` with status=INVITED | 7 years | role_requested field |
| Provisioning completion | `auth_users_profiles` + `auth_users_roles` creation | 7 years | Created by admin_approve_membership |
| Cache invalidation | `security_events`, type=`cache_cleared` | 1 year | On role change/revocation |

**Evidence Query**:
```sql
SELECT m.*, se.details->>'approver_id' as approver
FROM memberships m
JOIN security_events se ON se.details->>'membership_id' = m.id::text
WHERE m.yacht_id = :yacht_id
  AND se.event_type = 'admin_approve_success';
```

### CC6.3 — Access Removal
**Control**: The entity removes access to data when that access is no longer necessary.

| Evidence Type | Artifact Location | Retention | Notes |
|--------------|-------------------|-----------|-------|
| Membership revocations | `memberships` with status=REVOKED | 7 years | Includes reason |
| Role deactivations | `auth_users_roles` with is_active=FALSE | 7 years | Timestamped |
| Cache clear on revoke | Handler logs cache_cleared=True | 1 year | Immediate invalidation |
| Tenant cache eviction | `clear_tenant_cache()` calls | 1 year | Logged in handler |

---

## SOC2 CC7 — System Operations

### CC7.1 — Change Management
**Control**: The entity authorizes, designs, develops, configures, documents, tests, approves, and implements changes to systems.

| Evidence Type | Artifact Location | Retention | Notes |
|--------------|-------------------|-----------|-------|
| Registry gate validation | Startup logs `Registry validation PASSED` | 90 days | strict=True enforced |
| Action registry changes | Git history of `action_registry.py` | Indefinite | PR reviews required |
| Handler security contract | CI test results `test_handler_security_contract.py` | 90 days | Must pass for deploy |
| Router audit | `pms_audit_log` for all action executions | 7 years | request_id, idempotency_key |

### CC7.2 — Security Incident Response
**Control**: The entity responds to identified security incidents.

| Evidence Type | Artifact Location | Retention | Notes |
|--------------|-------------------|-----------|-------|
| Incident mode toggles | `system_flags` table | 7 years | incident_started_at, incident_reason |
| Incident enable/disable | `security_events`, type=`incident_mode_*` | 7 years | Started_by, ended_by |
| Yacht freeze events | `security_events`, type=`admin_freeze_*` | 7 years | Per-yacht kill switch |
| Blocked action attempts | Handler logs during incident | 90 days | 503 responses |

**Incident Evidence Query**:
```sql
SELECT * FROM security_events
WHERE event_type LIKE 'incident_mode%'
ORDER BY created_at DESC;
```

### CC7.3 — Monitoring
**Control**: The entity monitors system components for anomalies.

| Evidence Type | Artifact Location | Retention | Notes |
|--------------|-------------------|-----------|-------|
| Rate limit enforcement | Handler logs `rate_limited` | 90 days | Per-user burst exceeded |
| Concurrency limit hits | Handler logs `concurrency_limited` | 90 days | Per-yacht cap reached |
| Cross-yacht attempts | Handler logs `OwnershipValidationError` | 90 days | Returns 404 |
| Streaming safeguards | `min_prefix` rejections, cancellation logs | 90 days | Logged with query_hash |

---

## SOC2 CC8 — Risk Assessment

### CC8.1 — Risk Assessment Process
**Control**: The entity identifies and assesses risks to the achievement of its objectives.

| Evidence Type | Artifact Location | Retention | Notes |
|--------------|-------------------|-----------|-------|
| Security invariants doc | `docs/cybersecurity_handoff/02_INVARIANTS_DO_NOT_BREAK.md` | Indefinite | 10 invariants |
| High-risk area docs | `docs/cybersecurity_handoff/01_NEXT_ENGINEER_HANDOFF.md` | Indefinite | Service role, streaming, caching |
| Ownership validation | `test_ownership_validation.py` results | 90 days | Per-entity type coverage |
| Cross-yacht attack tests | `test_cross_yacht_attacks.py` results | 90 days | Fuzz testing |

---

## ISO 27001 Annex A.9 — Access Control

### A.9.1 — Business Requirements for Access Control
| Control | Evidence | Location |
|---------|----------|----------|
| A.9.1.1 Access control policy | Role definitions + required_roles on actions | `action_registry.py` |
| A.9.1.2 Access to networks | JWT validation + tenant isolation | `middleware/auth.py` |

### A.9.2 — User Access Management
| Control | Evidence | Location |
|---------|----------|----------|
| A.9.2.1 User registration | Invite → Accept → Provision workflow | `secure_admin_handlers.py` |
| A.9.2.2 User access provisioning | Membership + role assignment | MASTER + TENANT DBs |
| A.9.2.3 Privileged access | 2-person rule for privileged roles | `TwoPersonRuleViolation` error |
| A.9.2.4 User secret management | JWT secrets env-only, not in code | Render env vars |
| A.9.2.5 User access review | Quarterly review template | `QUARTERLY_ACCESS_REVIEW_TEMPLATE.md` |
| A.9.2.6 Access removal | Revocation workflow + cache clear | `admin_revoke_membership` |

### A.9.4 — System and Application Access Control
| Control | Evidence | Location |
|---------|----------|----------|
| A.9.4.1 Information access restriction | yacht_id scoping on all reads/writes | `WHERE yacht_id = ctx.yacht_id` |
| A.9.4.2 Secure log-on | Supabase GoTrue + JWT | `middleware/auth.py` |
| A.9.4.3 Password management | Supabase handles password policies | GoTrue config |
| A.9.4.4 Use of privileged utilities | Service role restricted, audit logged | Invariant #6 |

---

## ISO 27001 Annex A.12 — Operations Security

### A.12.1 — Operational Procedures
| Control | Evidence | Location |
|---------|----------|----------|
| A.12.1.1 Documented procedures | Runbooks for incident response | `docs/cybersecurity_handoff/08_PRODUCTION_RUNBOOKS.md` |
| A.12.1.2 Change management | Registry gate + CI tests | `secure_dispatcher.py` startup |

### A.12.4 — Logging and Monitoring
| Control | Evidence | Location |
|---------|----------|----------|
| A.12.4.1 Event logging | `pms_audit_log` + `security_events` | TENANT + MASTER DBs |
| A.12.4.2 Protection of logs | RLS on audit tables | Supabase RLS policies |
| A.12.4.3 Admin/operator logs | security_events with actor_id | MASTER DB |
| A.12.4.4 Clock synchronization | UTC timestamps, DB server time | All `created_at` columns |

---

## ISO 27001 Annex A.16 — Incident Management

### A.16.1 — Management of Incidents
| Control | Evidence | Location |
|---------|----------|----------|
| A.16.1.1 Responsibilities | Incident drill template with roles | `INCIDENT_DRILL_TEMPLATE.md` |
| A.16.1.2 Reporting events | Incident mode toggle audit | `admin_enable_incident_mode` |
| A.16.1.3 Reporting weaknesses | Security event logging | `security_events` table |
| A.16.1.4 Assessment | Incident reason field, postmortem | `incident_reason` in system_flags |
| A.16.1.5 Response | Kill switch + streaming disable | `check_incident_mode_for_action()` |
| A.16.1.6 Learning from incidents | Resolution notes field | `resolution_notes` in system_flags |
| A.16.1.7 Collection of evidence | Audit export tool | `export_audit_evidence.py` |

---

## Evidence Bundle Contents

When generating evidence for audit, the bundle should include:

### Required Files
```
evidence/<yacht_id>/<timestamp>/
├── index.json                    # Metadata: exporter version, git commit, command args
├── memberships.jsonl             # Membership transitions
├── role_changes.jsonl            # Role change events
├── admin_actions.jsonl           # All admin action audits
├── router_audits.jsonl           # Action router execution logs
├── storage_signing.jsonl         # Signed URL generation events
├── incident_events.jsonl         # Incident mode toggles
├── cache_invalidations.jsonl     # Cache clear events
├── summary.csv                   # Human-readable summary
└── README.md                     # How to interpret the bundle
```

### Redaction Rules
- **INCLUDE**: payload_hash, entity IDs, timestamps, actor IDs, outcome
- **EXCLUDE**: raw payload content, email addresses (hash instead), file contents
- **SANITIZE**: No tenant aliases in error messages, no table names in user-facing fields

### Retention Schedule
| Data Type | Retention Period | Justification |
|-----------|-----------------|---------------|
| Membership records | 7 years | SOC2 CC6, legal |
| Role changes | 7 years | SOC2 CC6 |
| Audit logs | 7 years | SOC2 CC7, ISO A.12 |
| Security events | 7 years | ISO A.16 |
| Handler logs | 90 days | Operational |
| Cache events | 1 year | Operational |

---

## Quarterly Review Schedule

| Quarter | Review Period | Due Date | Reviewer |
|---------|--------------|----------|----------|
| Q1 | Jan 1 - Mar 31 | Apr 15 | Security Lead |
| Q2 | Apr 1 - Jun 30 | Jul 15 | Security Lead |
| Q3 | Jul 1 - Sep 30 | Oct 15 | Security Lead |
| Q4 | Oct 1 - Dec 31 | Jan 15 | Security Lead |

---

## Audit Preparation Checklist

- [ ] Export evidence bundle for audit period
- [ ] Verify all membership transitions have approver records
- [ ] Confirm 2-person rule enforcement for privileged roles
- [ ] Review incident mode toggle history
- [ ] Check for anomalous access patterns
- [ ] Validate cache invalidation on role changes
- [ ] Ensure CI tests passed for all deployments in period
- [ ] Prepare quarterly access review attestation
