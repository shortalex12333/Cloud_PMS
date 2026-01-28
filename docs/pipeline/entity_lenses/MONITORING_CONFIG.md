# Monitoring & Alerting Configuration

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Purpose**: Security alerts, performance metrics, and operational monitoring

---

# OVERVIEW

This document defines monitoring, alerting, and logging requirements for the Entity Lens Architecture.

---

# 1. SECURITY ALERTS

## Critical Alerts (P0 - Immediate Response)

| Alert Name | Condition | Severity | Action |
|------------|-----------|----------|--------|
| `cross_yacht_access_attempt` | RLS denial with different yacht_id | CRITICAL | Block + notify security team |
| `mass_data_export` | >1000 records in single query | CRITICAL | Log + review |
| `unauthorized_role_escalation` | Role assignment without HoD auth | CRITICAL | Block + alert |
| `signature_bypass_attempt` | Action requiring signature without signature | CRITICAL | Block + log |
| `bulk_delete_attempt` | >10 deletes in 1 minute | CRITICAL | Block + review |

## High Alerts (P1 - Same Day Response)

| Alert Name | Condition | Severity | Action |
|------------|-----------|----------|--------|
| `excessive_rls_denials` | >5 RLS denials from same user in 5 min | HIGH | Log + review |
| `unusual_access_pattern` | API access outside normal hours | HIGH | Log + review |
| `failed_login_spike` | >10 failed logins in 5 min | HIGH | Temporary lockout |
| `service_role_misuse` | Service role used for user actions | HIGH | Alert + review |

## Warning Alerts (P2 - Weekly Review)

| Alert Name | Condition | Severity | Action |
|------------|-----------|----------|--------|
| `slow_query_detected` | Query >1s execution time | WARNING | Log + optimize |
| `low_stock_threshold` | Part below minimum quantity | WARNING | Create shopping list |
| `certificate_expiring` | Certificate expires in <30 days | WARNING | Notify + create WO |
| `overdue_work_order` | WO past due date by >7 days | WARNING | Notify assigned |

---

# 2. PERFORMANCE METRICS

## Query Latency

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| `query_latency_p50` | 100ms | 300ms |
| `query_latency_p90` | 300ms | 800ms |
| `query_latency_p99` | 500ms | 1500ms |
| `query_latency_max` | 1000ms | 3000ms |

## Action Success Rate

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| `action_success_rate` | 99.9% | 95% |
| `action_error_rate` | 0.1% | 5% |
| `rls_pass_rate` | 99.99% | 99% |

## System Health

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| `database_connections` | <50% pool | 80% pool |
| `storage_usage` | <70% | 85% |
| `api_response_time` | <200ms | 500ms |
| `edge_function_errors` | <1% | 5% |

---

# 3. AUDIT LOG MONITORING

## Required Audit Events

All of these events MUST be logged to `pms_audit_log`:

```yaml
audit_events:
  - name: entity_create
    required: true
    entities: [work_order, fault, equipment, part, certificate]

  - name: entity_update
    required: true
    entities: [all]
    include_diff: true

  - name: status_change
    required: true
    entities: [work_order, fault, equipment, shopping_list_item]
    include_old_value: true

  - name: signature_capture
    required: true
    entities: [work_order, receiving_event]
    signature_type: [completion, approval, verification]

  - name: stock_adjustment
    required: true
    entities: [part]
    include_reason: true
    large_adjustment_signature: ">50% change"

  - name: role_change
    required: true
    entities: [auth_users_roles]
    include_assigned_by: true
```

## Audit Log Retention

| Environment | Retention | Archive |
|-------------|-----------|---------|
| Production | 2 years | Cold storage after 90 days |
| Staging | 30 days | Delete |
| Development | 7 days | Delete |

---

# 4. REAL-TIME MONITORING DASHBOARD

## Key Metrics Panel

```yaml
dashboard:
  refresh_interval: 30s

  panels:
    - name: Active Users
      metric: active_sessions_count
      visualization: number

    - name: Actions/Minute
      metric: actions_per_minute
      visualization: sparkline

    - name: Error Rate
      metric: action_error_rate
      visualization: gauge
      thresholds: [1%, 3%, 5%]

    - name: Query Latency
      metric: query_latency_p90
      visualization: timeseries

    - name: RLS Denials
      metric: rls_denial_count
      visualization: number
      alert_on: >0

    - name: Open Work Orders
      metric: open_work_orders_count
      visualization: number

    - name: Low Stock Items
      metric: low_stock_parts_count
      visualization: number
      alert_on: >10

    - name: Expiring Certificates
      metric: certificates_expiring_30_days
      visualization: number
      alert_on: >0
```

---

# 5. LOG AGGREGATION

## Log Format

All application logs should follow this format:

```json
{
  "timestamp": "2026-01-25T10:30:00.123Z",
  "level": "INFO|WARN|ERROR|CRITICAL",
  "service": "api|edge-function|worker",
  "yacht_id": "uuid",
  "user_id": "uuid",
  "session_id": "uuid",
  "action": "action_name",
  "entity_type": "entity_type",
  "entity_id": "uuid",
  "duration_ms": 123,
  "success": true,
  "error_code": null,
  "message": "Human readable message",
  "metadata": {}
}
```

## Log Levels

| Level | Usage |
|-------|-------|
| DEBUG | Development only, verbose |
| INFO | Normal operations |
| WARN | Recoverable issues |
| ERROR | Failed operations |
| CRITICAL | Security/data issues |

---

# 6. HEALTH CHECKS

## Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Basic health | `{ "status": "ok" }` |
| `/health/db` | Database connectivity | `{ "status": "ok", "latency_ms": 10 }` |
| `/health/storage` | Storage connectivity | `{ "status": "ok" }` |
| `/health/auth` | Auth service | `{ "status": "ok" }` |

## Health Check Intervals

| Check | Interval | Timeout | Failure Threshold |
|-------|----------|---------|-------------------|
| Database | 30s | 5s | 3 failures |
| Storage | 60s | 10s | 3 failures |
| Auth | 60s | 5s | 3 failures |
| Edge Functions | 60s | 10s | 3 failures |

---

# 7. INCIDENT RESPONSE

## Escalation Matrix

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| P0 Critical | 15 minutes | Engineering lead immediately |
| P1 High | 1 hour | Engineering lead same day |
| P2 Warning | 24 hours | Engineering team weekly review |
| P3 Info | 1 week | Product review |

## Runbooks

| Incident Type | Runbook Location |
|---------------|------------------|
| Cross-yacht data leak | `/runbooks/security/cross-yacht-leak.md` |
| Database connection exhaustion | `/runbooks/database/connection-pool.md` |
| High error rate | `/runbooks/application/error-spike.md` |
| Storage quota exceeded | `/runbooks/storage/quota-exceeded.md` |

---

# 8. COMPLIANCE REPORTING

## Required Reports

| Report | Frequency | Audience |
|--------|-----------|----------|
| Security audit summary | Monthly | Management |
| Data access log | On-demand | Compliance |
| User activity report | Weekly | Yacht management |
| System health summary | Daily | Engineering |

## Data Retention Compliance

| Data Type | Retention | Regulation |
|-----------|-----------|------------|
| Audit logs | 2 years | Maritime compliance |
| User data | Account lifetime + 1 year | GDPR |
| Work order history | 5 years | Maritime compliance |
| Certificate records | Certificate life + 2 years | Maritime compliance |

---

# 9. ALERTING CHANNELS

## Channel Configuration

```yaml
alerting:
  channels:
    - name: slack_engineering
      type: slack
      webhook: $SLACK_ENGINEERING_WEBHOOK
      severities: [CRITICAL, HIGH, WARNING]

    - name: pagerduty_oncall
      type: pagerduty
      service_key: $PAGERDUTY_SERVICE_KEY
      severities: [CRITICAL]

    - name: email_management
      type: email
      recipients: [management@celeste.yacht]
      severities: [CRITICAL, HIGH]

    - name: sms_oncall
      type: sms
      numbers: $ONCALL_PHONE_NUMBERS
      severities: [CRITICAL]
```

---

# 10. IMPLEMENTATION CHECKLIST

## Pre-Production Requirements

- [ ] All P0 alerts configured and tested
- [ ] Dashboard deployed and accessible
- [ ] Log aggregation working
- [ ] Health checks returning correctly
- [ ] Runbooks documented
- [ ] Escalation contacts verified
- [ ] Alerting channels tested
- [ ] Retention policies implemented
- [ ] Compliance reports generating

---

**END OF MONITORING CONFIGURATION**
