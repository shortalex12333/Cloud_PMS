# Evidence Plan (SOC2 / ISO) — What auditors will ask for

## Access control evidence
- Membership invite/approve/revoke audit logs
- Quarterly access review records
- Step-up auth policy and logs for privileged actions

## Change management evidence
- PR reviews (2-person for policy/auth changes)
- CI logs showing isolation tests executed
- Deployment logs

## Monitoring/IR evidence
- Alert definitions (deny spikes, role changes, streaming floods)
- Incident drill records (tabletop)
- IR playbook + post-incident RCA template

## Data protection evidence
- Encryption-in-transit configuration
- Encryption-at-rest statement (provider)
- Key rotation runbook and rotation records

## Practical note
SOC2 Type II is about **consistent execution**. If you can't produce artifacts,
you will fail even if your code is good.
