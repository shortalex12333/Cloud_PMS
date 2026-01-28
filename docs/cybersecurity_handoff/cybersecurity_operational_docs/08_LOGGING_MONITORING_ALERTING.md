# Logging, Monitoring, Alerting (Production)

## What to log (structured)
- request_id
- user_id
- yacht_id
- membership_id
- role
- action_name
- outcome (allow/deny/error)
- latency_ms
- rows_read / rows_written
- error_code (not stack traces to client)

## What NOT to log by default
- document contents
- full search query text
- secrets/tokens
- PII beyond what is necessary

## Alerts (high signal)
- Any cross-yacht ownership validation failure spikes
- Any access denied for privileged actions (possible probing)
- Role changes for captain/manager
- Sudden increase in streaming query rate
- Failed login spikes / locked accounts
- Unexpected tenant_key_alias switches for same user
- Storage signed URL generation spikes

## Dashboards (internal only)
- Actions per yacht per hour
- Denies by action group
- Streaming concurrency
- Audit write failure rate (must be ~0)
- Error budget and SLOs

## Retention
- Security logs retained per policy (define period; common 90–365 days)
- Audit logs retained longer (legal; often 1–7 years depending on contracts)
