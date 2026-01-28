# Quarterly Access Review Template

## Review Information

| Field | Value |
|-------|-------|
| **Review Period** | [YYYY-MM-DD] to [YYYY-MM-DD] |
| **Yacht ID** | [YACHT_ID] |
| **Yacht Name** | [YACHT_NAME] |
| **Reviewer** | [NAME] |
| **Review Date** | [YYYY-MM-DD] |
| **Next Review Due** | [YYYY-MM-DD] |

---

## 1. Yacht Scope

### Yacht Details
- **Yacht ID**: ________________________
- **Fleet Registry Status**: [ ] ACTIVE  [ ] INACTIVE  [ ] FROZEN
- **Tenant Key Alias**: ________________________
- **Is Frozen**: [ ] YES  [ ] NO

### Review Query
```sql
SELECT yacht_id, yacht_name, active, is_frozen, tenant_key_alias
FROM fleet_registry
WHERE yacht_id = :yacht_id;
```

---

## 2. Active Memberships

### Summary
| Metric | Count |
|--------|-------|
| Total Active Memberships | _____ |
| Privileged Roles (captain/manager/chief_engineer) | _____ |
| Standard Roles (crew/guest/other) | _____ |
| Memberships Added This Quarter | _____ |
| Memberships Revoked This Quarter | _____ |

### Active Membership List

| User ID | Role | Status | Valid From | Valid Until | Last Activity |
|---------|------|--------|------------|-------------|---------------|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

### Review Query
```sql
SELECT
  m.user_id,
  r.role,
  m.status,
  r.valid_from,
  r.valid_until,
  m.created_at
FROM memberships m
JOIN auth_users_roles r ON r.user_id = m.user_id AND r.yacht_id = m.yacht_id
WHERE m.yacht_id = :yacht_id
  AND m.status = 'ACTIVE'
  AND r.is_active = TRUE
ORDER BY r.role, m.created_at;
```

---

## 3. Privileged Role Review (2-Person Approval)

### Privileged Roles Granted This Quarter

For each privileged role (captain, manager, chief_engineer), verify 2-person rule compliance:

| User ID | Role | Invited By | Approved By | 2-Person OK? |
|---------|------|------------|-------------|--------------|
| | | | | [ ] YES [ ] NO |
| | | | | [ ] YES [ ] NO |
| | | | | [ ] YES [ ] NO |

### Verification Checklist
- [ ] All captain role grants have different inviter and approver
- [ ] All manager role grants have different inviter and approver
- [ ] All chief_engineer role grants have different inviter and approver
- [ ] No self-escalation to privileged roles detected

### Review Query
```sql
SELECT
  m.user_id,
  m.role_requested,
  m.invited_by,
  m.approved_by,
  CASE WHEN m.invited_by != m.approved_by THEN 'OK' ELSE 'VIOLATION' END as two_person_check,
  m.created_at,
  m.status
FROM memberships m
WHERE m.yacht_id = :yacht_id
  AND m.role_requested IN ('captain', 'manager', 'chief_engineer')
  AND m.created_at >= :start_date
  AND m.created_at <= :end_date;
```

---

## 4. Role Changes This Quarter

| User ID | Old Role | New Role | Changed By | Date | Justification |
|---------|----------|----------|------------|------|---------------|
| | | | | | |
| | | | | | |

### Review Query
```sql
SELECT
  se.user_id,
  se.details->>'old_role' as old_role,
  se.details->>'new_role' as new_role,
  se.details->>'actor_id' as changed_by,
  se.created_at,
  se.details->>'reason' as justification
FROM security_events se
WHERE se.yacht_id = :yacht_id
  AND se.event_type = 'admin_change_role_success'
  AND se.created_at >= :start_date
  AND se.created_at <= :end_date;
```

---

## 5. Revocations This Quarter

| User ID | Previous Role | Revoked By | Date | Reason |
|---------|---------------|------------|------|--------|
| | | | | |
| | | | | |

### Review Query
```sql
SELECT
  m.user_id,
  m.role_requested as previous_role,
  se.details->>'actor_id' as revoked_by,
  se.created_at,
  se.details->>'reason' as reason
FROM memberships m
JOIN security_events se ON se.details->>'membership_id' = m.id::text
WHERE m.yacht_id = :yacht_id
  AND m.status = 'REVOKED'
  AND se.event_type = 'admin_revoke_success'
  AND se.created_at >= :start_date
  AND se.created_at <= :end_date;
```

---

## 6. Anomalies Detected

### Access Anomalies
| Type | Description | User ID | Date | Action Taken |
|------|-------------|---------|------|--------------|
| | | | | |
| | | | | |

### Common Anomaly Types
- [ ] Inactive user with recent action attempts
- [ ] Role used after revocation (cache timing)
- [ ] Cross-yacht access attempt detected
- [ ] Rate limit exceeded repeatedly
- [ ] Unusual action patterns

### Anomaly Detection Query
```sql
-- Find rate limit violations
SELECT
  user_id,
  COUNT(*) as violation_count,
  MIN(created_at) as first_violation,
  MAX(created_at) as last_violation
FROM pms_audit_log
WHERE yacht_id = :yacht_id
  AND outcome = 'rate_limited'
  AND created_at >= :start_date
GROUP BY user_id
HAVING COUNT(*) > 5;
```

---

## 7. Cache Invalidation Verification

### Cache Clear Events
| Event Type | User ID | Trigger | Date |
|------------|---------|---------|------|
| Role Change | | | |
| Revocation | | | |
| Yacht Freeze | | | |

### Verification
- [ ] All role changes triggered cache invalidation
- [ ] All revocations triggered cache invalidation
- [ ] Cache TTL is bounded (< 2 minutes)

---

## 8. Attestation

### Reviewer Attestation

I, the undersigned, have reviewed the access controls for the yacht identified above for the specified review period. I attest that:

- [ ] All active memberships have been reviewed and are appropriate
- [ ] Privileged role assignments comply with the 2-person rule
- [ ] Role changes have proper justification
- [ ] Revocations were processed correctly with cache invalidation
- [ ] No unresolved anomalies exist OR all anomalies have documented remediation

**Reviewer Signature**: ________________________

**Date**: ________________________

### Manager Approval (if anomalies found)

- [ ] All anomalies have been reviewed and addressed
- [ ] Remediation actions are documented
- [ ] No outstanding security concerns

**Manager Signature**: ________________________

**Date**: ________________________

---

## 9. Appendix

### Evidence Bundle Location
```
evidence/<yacht_id>/<review_period>/bundle.zip
```

### Export Command Used
```bash
python scripts/compliance/export_audit_evidence.py \
  --yacht-id <YACHT_ID> \
  --start <START_DATE> \
  --end <END_DATE> \
  --out evidence/<yacht_id>/<review_period>
```

### Related Documents
- Evidence Checklist: `EVIDENCE_CHECKLIST_SOC2_ISO.md`
- Incident Drill Template: `INCIDENT_DRILL_TEMPLATE.md`
- Security Handoff: `docs/cybersecurity_handoff/01_NEXT_ENGINEER_HANDOFF.md`

---

## Review Cadence

| Quarter | Review Period | Due Date | Status |
|---------|--------------|----------|--------|
| Q1 2026 | Jan 1 - Mar 31 | Apr 15 | [ ] Complete |
| Q2 2026 | Apr 1 - Jun 30 | Jul 15 | [ ] Complete |
| Q3 2026 | Jul 1 - Sep 30 | Oct 15 | [ ] Complete |
| Q4 2026 | Oct 1 - Dec 31 | Jan 15 | [ ] Complete |
