#!/usr/bin/env bash
# =============================================================================
# Seed Document Test Data via Supabase REST API
# =============================================================================
# Seeds 15 test documents into doc_metadata table for E2E tests
# Documents include technical manuals, safety procedures, certificates, etc.
#
# Usage: ./seed-documents-via-api.sh

set -e

# Load environment variables
if [ -f ".env.e2e.local" ]; then
  export $(grep -v '^#' .env.e2e.local | xargs)
fi

TENANT_URL="${TENANT_SUPABASE_URL}"
SERVICE_KEY="${TENANT_SUPABASE_SERVICE_KEY}"
YACHT_ID="${YACHT_ID}"

if [ -z "$TENANT_URL" ] || [ -z "$SERVICE_KEY" ] || [ -z "$YACHT_ID" ]; then
  echo "❌ Error: Missing required environment variables"
  echo "Required: TENANT_SUPABASE_URL, TENANT_SUPABASE_SERVICE_KEY, YACHT_ID"
  exit 1
fi

echo "🚀 Seeding document test data..."
echo "Tenant URL: $TENANT_URL"
echo "Yacht ID: $YACHT_ID"
echo ""

# Function to insert a document
insert_document() {
  local document_name=$1
  local file_type=$2
  local description=$3
  local tags=$4

  echo "📄 Inserting: $document_name"

  curl -s -X POST "$TENANT_URL/rest/v1/doc_metadata" \
    -H "apikey: $SERVICE_KEY" \
    -H "Authorization: Bearer $SERVICE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=minimal" \
    -d "{
      \"yacht_id\": \"$YACHT_ID\",
      \"document_name\": \"$document_name\",
      \"file_type\": \"$file_type\",
      \"description\": \"$description\",
      \"tags\": \"$tags\",
      \"file_url\": \"https://storage.celeste7.ai/documents/test_$file_type.pdf\",
      \"uploaded_by_name\": \"Test User\",
      \"uploaded_at\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"
    }"

  if [ $? -eq 0 ]; then
    echo "  ✓ Inserted successfully"
  else
    echo "  ✗ Failed to insert"
  fi
}

# Seed 15 diverse test documents
insert_document "Engine Maintenance Manual" "pdf" "Complete maintenance procedures for main engines" "maintenance,engine,manual"
insert_document "Safety Procedures 2026" "pdf" "Updated safety procedures and protocols" "safety,procedures,compliance"
insert_document "Crew Training Certificate" "pdf" "STCW training certificates for crew" "certificates,crew,training"
insert_document "Fuel System Diagram" "pdf" "Technical diagram of fuel delivery system" "technical,diagram,fuel"
insert_document "Emergency Response Plan" "pdf" "Emergency procedures and contact information" "emergency,safety,procedures"
insert_document "Navigation Equipment Manual" "pdf" "Operating manual for navigation systems" "navigation,equipment,manual"
insert_document "Fire Safety Checklist" "pdf" "Monthly fire safety inspection checklist" "safety,checklist,fire"
insert_document "HVAC System Specifications" "pdf" "Technical specifications for HVAC system" "technical,hvac,specifications"
insert_document "Vessel Registration" "pdf" "Official vessel registration documents" "certificates,registration,compliance"
insert_document "Electrical System Schematic" "pdf" "Complete electrical system wiring diagram" "technical,electrical,diagram"
insert_document "Lifeboat Inspection Report" "pdf" "Annual lifeboat and davit inspection" "safety,inspection,lifeboat"
insert_document "Waste Management Plan" "pdf" "Environmental compliance waste procedures" "environmental,compliance,procedures"
insert_document "Radio Communication Log" "pdf" "VHF radio communication logs" "communication,log,operations"
insert_document "Stability Booklet" "pdf" "Vessel stability calculations and limits" "technical,stability,compliance"
insert_document "Port Clearance Documents" "pdf" "Customs and immigration clearance forms" "certificates,clearance,compliance"

echo ""
echo "✅ Document seeding complete!"
echo ""
echo "Verifying documents in database..."

# Verify count
COUNT=$(curl -s "$TENANT_URL/rest/v1/doc_metadata?yacht_id=eq.$YACHT_ID&select=count" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "Range: 0-0" \
  -H "Prefer: count=exact" | jq -r '.[0].count // 0')

echo "Total documents in database: $COUNT"

if [ "$COUNT" -ge "15" ]; then
  echo "✅ SUCCESS: At least 15 documents seeded"
else
  echo "⚠️  WARNING: Expected 15+ documents, found $COUNT"
fi
