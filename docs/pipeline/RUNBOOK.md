Runbook (Commands)
==================

Docker Acceptance (fast loop)
- ./scripts/test-local-docker.sh
- or: docker-compose -f docker-compose.test.yml up --build

Staging Acceptance (CI)
- GitHub Actions → "Staging Certificates Acceptance" → Run workflow
- Make this workflow a required check on main
- Use stable CI accounts; avoid DB pollution:
    - Set CREATE_USERS='false' in workflow
    - Secrets: STAGING_CREW_EMAIL=crew.test@alex-short.com
              STAGING_HOD_EMAIL=hod.test@alex-short.com
              STAGING_CAPTAIN_EMAIL=captain.test@alex-short.com
              STAGING_USER_PASSWORD=<password>

Manual Staging Quick Test
1) Create + map user in MASTER, provision TENANT profile/role
2) Login to MASTER for JWT
3) POST /v1/actions/execute
   - create_vessel_certificate → expect 200
   - link_document_to_certificate (invalid document_id) → expect 400/404
   - update_certificate → expect 200 (no audit 409)

Render Deploy Hook (staging)
- POST https://api.render.com/deploy/srv-d5fr5hre5dus73d3gdn0?key=...

