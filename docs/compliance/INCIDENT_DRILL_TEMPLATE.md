# Security Incident Response Drill Template

## Drill Information

| Field | Value |
|-------|-------|
| **Drill ID** | INC-DRILL-[YYYY-MM-DD] |
| **Drill Date** | [YYYY-MM-DD HH:MM UTC] |
| **Drill Type** | [ ] Tabletop  [ ] Live (staging)  [ ] Live (production) |
| **Scenario** | [Scenario Name] |
| **Duration** | [Expected Duration] |
| **Coordinator** | [NAME] |

---

## 1. Pre-Drill Checklist

### Environment Preparation
- [ ] Staging environment available (if live drill)
- [ ] Test user accounts created with various roles
- [ ] Test yacht provisioned with sample data
- [ ] Monitoring dashboards accessible
- [ ] Communication channels ready (Slack/Teams incident channel)

### Participant Notification
- [ ] All participants notified of drill date/time
- [ ] Roles assigned (see Section 3)
- [ ] Runbook distributed
- [ ] Emergency abort procedure communicated

### Tools Ready
- [ ] Admin console access verified
- [ ] Audit export tool tested
- [ ] Database query access (read-only)
- [ ] Log aggregation access

---

## 2. Drill Scenario

### Scenario: Suspected Cross-Tenant Data Leak

**Background**: Security team received an alert that user `USER-SUSPICIOUS` from Yacht A may have accessed documents belonging to Yacht B through a potential API vulnerability.

**Objectives**:
1. Enable incident mode to halt sensitive operations
2. Verify streaming and signed URLs are blocked
3. Investigate audit logs for cross-yacht access attempts
4. Export evidence for analysis
5. Restore normal operations after investigation

**Success Criteria**:
- Incident mode enabled within 5 minutes of detection
- All MUTATE/SIGNED/ADMIN actions blocked during incident
- Streaming search returns 503 when disabled
- Evidence bundle exported and contains required artifacts
- System restored within 30 minutes total

---

## 3. Roles and Responsibilities

| Role | Name | Responsibilities |
|------|------|------------------|
| **Incident Commander** | | Overall coordination, decision authority |
| **Security Analyst** | | Log analysis, threat assessment |
| **Platform Engineer** | | System operations, kill switch execution |
| **Communications Lead** | | Status updates, stakeholder comms |
| **Scribe** | | Timeline documentation, artifact collection |

---

## 4. Drill Steps

### Phase 1: Detection & Escalation (T+0 to T+5 min)

| Step | Action | Command/Location | Expected Result | Actual Result | Time |
|------|--------|-----------------|-----------------|---------------|------|
| 1.1 | Alert received | Monitoring/Slack | Alert with user_id, action, timestamp | | |
| 1.2 | Incident Commander notified | Comm channel | Acknowledgment | | |
| 1.3 | Drill start announced | Comm channel | All participants aware | | |

### Phase 2: Containment (T+5 to T+10 min)

| Step | Action | Command/Location | Expected Result | Actual Result | Time |
|------|--------|-----------------|-----------------|---------------|------|
| 2.1 | Enable incident mode | Admin API or DB | `incident_mode=TRUE` | | |

**Enable Incident Mode Command**:
```bash
# Via Admin API
curl -X POST https://api.example.com/admin/incident/enable \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "reason": "DRILL: Suspected cross-tenant access",
    "disable_streaming": true,
    "disable_signed_urls": true,
    "disable_writes": true
  }'

# Or via direct DB (emergency only)
UPDATE system_flags SET
  incident_mode = TRUE,
  disable_streaming = TRUE,
  disable_signed_urls = TRUE,
  disable_writes = TRUE,
  incident_reason = 'DRILL: Suspected cross-tenant access',
  incident_started_at = NOW(),
  incident_started_by = 'admin-user-id'
WHERE id = 1;
```

| Step | Action | Command/Location | Expected Result | Actual Result | Time |
|------|--------|-----------------|-----------------|---------------|------|
| 2.2 | Verify incident mode active | GET /admin/system-flags | `incident_mode: true` | | |
| 2.3 | Test MUTATE action blocked | POST /api/action/update_* | 503 response | | |
| 2.4 | Test streaming blocked | GET /api/search/stream | 503 response | | |
| 2.5 | Verify audit log entry | security_events table | `incident_mode_enabled` event | | |

### Phase 3: Investigation (T+10 to T+20 min)

| Step | Action | Command/Location | Expected Result | Actual Result | Time |
|------|--------|-----------------|-----------------|---------------|------|
| 3.1 | Query cross-yacht attempts | Audit logs | List of 404 responses | | |
| 3.2 | Identify suspicious user | pms_audit_log | Actions by USER-SUSPICIOUS | | |
| 3.3 | Check ownership validations | Handler logs | OwnershipValidationError entries | | |
| 3.4 | Export evidence bundle | export_audit_evidence.py | bundle.zip created | | |

**Investigation Queries**:
```sql
-- Find cross-yacht access attempts (should all be 404)
SELECT
  user_id,
  action_name,
  yacht_id,
  outcome,
  created_at
FROM pms_audit_log
WHERE created_at >= NOW() - INTERVAL '1 hour'
  AND outcome = 'denied'
ORDER BY created_at DESC;

-- Check specific user activity
SELECT *
FROM pms_audit_log
WHERE user_id = 'USER-SUSPICIOUS'
  AND created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

**Export Evidence**:
```bash
python scripts/compliance/export_audit_evidence.py \
  --yacht-id YACHT-A \
  --user-id USER-SUSPICIOUS \
  --start 2026-01-27T00:00:00Z \
  --end 2026-01-28T23:59:59Z \
  --out evidence/drill-$(date +%Y%m%d)
```

### Phase 4: Resolution (T+20 to T+25 min)

| Step | Action | Command/Location | Expected Result | Actual Result | Time |
|------|--------|-----------------|-----------------|---------------|------|
| 4.1 | Review findings | Incident channel | Summary of investigation | | |
| 4.2 | Decision: all clear | Incident Commander | Authorization to restore | | |
| 4.3 | Disable incident mode | Admin API | `incident_mode=FALSE` | | |

**Disable Incident Mode Command**:
```bash
curl -X POST https://api.example.com/admin/incident/disable \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "resolution_notes": "DRILL: No actual breach. System functioned correctly."
  }'
```

| Step | Action | Command/Location | Expected Result | Actual Result | Time |
|------|--------|-----------------|-----------------|---------------|------|
| 4.4 | Verify normal operations | Test API calls | 200 responses | | |
| 4.5 | Verify streaming restored | GET /api/search/stream | Streaming works | | |
| 4.6 | Confirm audit trail | security_events | `incident_mode_disabled` event | | |

### Phase 5: Post-Drill (T+25 to T+30 min)

| Step | Action | Command/Location | Expected Result | Actual Result | Time |
|------|--------|-----------------|-----------------|---------------|------|
| 5.1 | Announce drill complete | Comm channel | All participants notified | | |
| 5.2 | Collect artifacts | evidence/ directory | All files present | | |
| 5.3 | Schedule debrief | Calendar | Meeting set | | |

---

## 5. Artifacts Checklist

### Required Drill Artifacts

| Artifact | Location | Collected? |
|----------|----------|------------|
| This completed template | docs/compliance/drills/ | [ ] |
| Incident enable screenshot/log | evidence/drill-*/ | [ ] |
| Blocked action attempt logs | evidence/drill-*/ | [ ] |
| Investigation query results | evidence/drill-*/ | [ ] |
| Evidence export bundle (bundle.zip) | evidence/drill-*/ | [ ] |
| Incident disable screenshot/log | evidence/drill-*/ | [ ] |
| Timeline log from Scribe | evidence/drill-*/ | [ ] |
| Participant sign-off | This document | [ ] |

### Evidence Bundle Contents (verify)
- [ ] index.json with exporter version and command
- [ ] memberships.jsonl
- [ ] role_changes.jsonl
- [ ] admin_actions.jsonl
- [ ] incident_events.jsonl
- [ ] summary.csv
- [ ] README.md

---

## 6. Success Criteria Assessment

| Criterion | Target | Actual | Pass? |
|-----------|--------|--------|-------|
| Time to enable incident mode | < 5 min | | [ ] |
| MUTATE actions blocked | 100% | | [ ] |
| Streaming blocked (if configured) | 100% | | [ ] |
| Signed URLs blocked (if configured) | 100% | | [ ] |
| Evidence bundle complete | All files | | [ ] |
| Total drill duration | < 30 min | | [ ] |
| No real data impacted | TRUE | | [ ] |

### Overall Drill Result
- [ ] **PASS** - All criteria met
- [ ] **PARTIAL** - Some criteria not met (document in findings)
- [ ] **FAIL** - Critical failures (immediate remediation required)

---

## 7. Findings and Recommendations

### What Worked Well
1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

### Areas for Improvement
| Finding | Severity | Recommendation | Owner | Due Date |
|---------|----------|----------------|-------|----------|
| | | | | |
| | | | | |
| | | | | |

### Action Items
- [ ] _____________________________________
- [ ] _____________________________________
- [ ] _____________________________________

---

## 8. Participant Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Incident Commander | | | |
| Security Analyst | | | |
| Platform Engineer | | | |
| Communications Lead | | | |
| Scribe | | | |

---

## 9. Appendix

### Emergency Abort Procedure
If the drill must be aborted:
1. Announce "DRILL ABORT" in incident channel
2. Immediately disable incident mode
3. Verify normal operations restored
4. Document reason for abort
5. Reschedule drill

### Escalation Contacts
| Role | Name | Phone | Email |
|------|------|-------|-------|
| Security Lead | | | |
| Platform Lead | | | |
| On-Call Engineer | | | |

### Related Documents
- Evidence Checklist: `EVIDENCE_CHECKLIST_SOC2_ISO.md`
- Access Review Template: `QUARTERLY_ACCESS_REVIEW_TEMPLATE.md`
- Production Runbooks: `docs/cybersecurity_handoff/08_PRODUCTION_RUNBOOKS.md`

---

## Drill Cadence

| Quarter | Drill Type | Scenario | Date | Status |
|---------|------------|----------|------|--------|
| Q1 2026 | Tabletop | Cross-tenant access | | [ ] Complete |
| Q2 2026 | Live (staging) | Compromised credentials | | [ ] Complete |
| Q3 2026 | Tabletop | Data exfiltration | | [ ] Complete |
| Q4 2026 | Live (staging) | Service disruption | | [ ] Complete |
