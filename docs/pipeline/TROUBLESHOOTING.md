# Troubleshooting

Common issues and fast fixes for this pipeline.

---

## Invalid document link returns 500 in staging
Symptoms: POST `link_document_to_certificate` with fake `document_id` returns 500.

Fix:
- Redeploy staging pipeline service to pick up latest handler/dispatcher
- Run staging CI (required) — it asserts 400/404 for invalid docs

---

## No action buttons under search bar
Symptoms: Query like "add certificate" shows no SuggestedActions.

Checks:
- Frontend env: `NEXT_PUBLIC_API_URL` points to staging API
- Browser network: `GET /v1/actions/list?...` returns 200 with actions
- Spotlight integrates `SuggestedActions` (SpotlightSearch.tsx) and passes `actionSuggestions` from `useCelesteSearch`

---

## CREW sees mutation actions
Symptoms: CREW user gets MUTATE/SIGNED suggestions.

Checks:
- Registry `allowed_roles` correct for domain actions
- `search_actions()` called with actual role from JWT
- Staging CI must fail if CREW sees mutation actions — review CI logs

---

## CI creates many timestamped users
Symptoms: DB pollution with `*.ci+<ts>@...` users.

Fix:
- Set `CREATE_USERS='false'` in staging workflow and provide stable user secrets
- Use cleanup snippets in PROVISIONING_RUNBOOK.md to remove polluted users

---

## Domain filter returns unrelated actions
Symptoms: `domain=certificates` returns non-certificate actions.

Fix:
- Ensure repo includes fixed filter in `registry.py`:
  ```python
  if domain and action.domain != domain:
      continue
  ```
- Add/verify Docker test cases for unknown domain

---

## Storage path looks wrong
Symptoms: Path preview shows wrong tenant or missing IDs.

Checks:
- Render has `DEFAULT_YACHT_CODE` and `y<ALIAS>_SUPABASE_*` vars set
- Suggestions use `entity_id` only when editing; for create, preview uses `<new_id>` until record is created
- Execution validates writable prefixes server‑side

