#!/bin/bash
# Deploy TRIGRAM functions to Supabase
# Run this from a machine with psql access to the database

# Database connection (update with your credentials)
DB_HOST="aws-0-us-west-2.pooler.supabase.com"
DB_PORT="6543"
DB_USER="postgres.vzsohavtuotocgrfkfyd"
DB_NAME="postgres"
DB_PASSWORD="${SUPABASE_DB_PASSWORD:-YOUR_PASSWORD}"

MIGRATION_FILE="../supabase/migrations/20260104_trigram_search.sql"

echo "Deploying TRIGRAM search functions..."

PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo "TRIGRAM functions deployed successfully!"
else
    echo "Deployment failed. Check database credentials."
    exit 1
fi
