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

---

Action Suggestions Endpoint
---------------------------

GET /v1/actions/list - Returns role-gated action suggestions.

Query params:
- q: Search query (e.g., "add certificate")
- domain: Filter by domain (e.g., "certificates")
- entity_id: Entity ID for storage path preview

Response includes:
- actions[]: List of available actions for user's role
- storage_options: For file-related actions (bucket, path_preview, confirmation_required)
- match_score: Relevance score for query matching

Example:
  curl -H "Authorization: Bearer $HOD_JWT" \
    "http://localhost:8000/v1/actions/list?q=add+certificate&domain=certificates"

Storage confirmation UX: When storage_options.confirmation_required is true, UI should
show a confirmation dialog before executing file-related actions. Presigned upload URLs
are generated only during /execute flow, not in suggestions.

Frontend Smoke (Spotlight)
--------------------------

- HOD types "add certificate" → SuggestedActions shows "Add Vessel Certificate" button
- CREW types "add certificate" → No mutation buttons
- Clicking a button opens ActionModal with required fields and storage path preview
- Submitting executes action and refreshes results
