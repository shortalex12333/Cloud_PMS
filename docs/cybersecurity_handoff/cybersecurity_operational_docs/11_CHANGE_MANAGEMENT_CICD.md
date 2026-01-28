# Change Management & CI/CD (SOC2 / ISO)

## Non-negotiable deployment rules
- All schema changes via migrations
- All policy changes reviewed by at least 2 people for production
- Isolation test suite must pass before deploy

## Required CI checks
- Static checks:
  - forbid direct TENANT client usage from frontend
  - ensure handlers use request_context
- Integration tests:
  - cross-yacht read/write attempts
  - role escalation attempts
  - streaming search tests (authz before bytes)
  - storage path traversal tests
- Performance checks:
  - query budgets for streaming endpoints

## Evidence artifacts (auditors)
- PR reviews and approvals
- CI logs proving test execution
- Deployment logs
- Change tickets (if you use them)
