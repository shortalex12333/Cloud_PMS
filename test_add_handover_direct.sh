#!/bin/bash
# Direct test of add_to_handover endpoint

set -e

# Get fresh token
echo "Getting JWT token..."
TOKEN=$(npx ts-node -e "
import { login } from './tests/helpers/auth';
login('x@alex-short.com', 'Password2!')
  .then(tokens => console.log(tokens.accessToken))
  .catch(err => { console.error(err); process.exit(1); });
" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token"
  exit 1
fi

echo "Token obtained, testing add_to_handover..."
echo ""

# Test with exact E2E payload
curl -i -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_to_handover",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "title": "Direct Test: Critical item",
      "summary": "Testing add_to_handover with correct payload",
      "category": "urgent",
      "section": "engineering",
      "is_critical": true,
      "priority": "high",
      "entity_type": "note"
    }
  }'

echo ""
echo "Test complete"
