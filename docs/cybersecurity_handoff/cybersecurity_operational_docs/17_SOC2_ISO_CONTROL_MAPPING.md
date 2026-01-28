# SOC 2 / ISO 27001 Control Mapping (Practical)

This is not a full matrix; it's the mapping scaffold you use to produce evidence.

## SOC 2 (Trust Services Criteria)
- CC6.x (Logical access):
  - Membership lifecycle, role gating, step-up auth, least privilege
- CC7.x (System operations):
  - Monitoring, alerting, incident response playbook, kill switch
- CC8.x (Change management):
  - CI/CD gates, reviews, migration controls, isolation tests

Evidence examples:
- PR approvals, CI logs, deployment records
- Audit log samples with request_id
- Alert definitions + incident drill logs
- Access review records (quarterly)

## ISO 27001 Annex A (common mappings)
- A.5 (Policies): security posture docs, access control policy
- A.8 (Asset management): asset inventory of data types and systems
- A.9 (Access control): memberships, role management, revocation
- A.10 (Cryptography): encryption at rest/in transit, key management roadmap
- A.12 (Ops security): logging, monitoring, vulnerability mgmt
- A.14 (System acquisition/dev): SDLC, testing, change control
- A.16 (Incident mgmt): IR playbook, containment controls
