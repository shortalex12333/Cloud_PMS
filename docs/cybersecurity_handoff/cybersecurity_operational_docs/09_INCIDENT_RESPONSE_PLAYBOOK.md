# Incident Response Playbook (Practical)

## Severity definitions
- SEV0: confirmed cross-yacht disclosure (potential $50m exposure)
- SEV1: suspected disclosure or active exploitation attempt
- SEV2: elevated risk indicators, no disclosure confirmed
- SEV3: minor security event

## Immediate containment (SEV0/SEV1)
1) Trigger global incident mode (MASTER flag)
   - disables streaming
   - disables signed URL generation
   - freezes all MUTATE/SIGNED actions (or per yacht)
2) Revoke affected user memberships
3) Revoke device tokens (agents) for affected yacht(s)
4) Rotate service credentials if suspected compromised
5) Preserve audit logs and export for forensics

## Investigation checklist
- Identify actor(s): user_id, device_id, IPs
- Identify scope: which yacht_id(s) touched
- Validate logs for cross-yacht anomalies
- Validate storage URL access logs
- Determine root cause category:
  - handler validation gap
  - RLS misconfig
  - credential compromise
  - insider misuse

## Recovery
- Patch and deploy with isolation tests expanded
- Re-enable streaming only after validation
- Customer notification per contract and law (jurisdiction-dependent)

## Post-incident
- Write RCA
- Add new test that would have caught it
- Update guardrails doc and training
