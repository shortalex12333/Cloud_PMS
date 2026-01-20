# OAuth Token Table Schema

## Table: auth_microsoft_tokens

### Columns

(Schema from migration file - information_schema query failed)

| Column | Type | Nullable |
|--------|------|----------|
| id | uuid | NO |
| user_id | uuid | NO |
| yacht_id | uuid | NO |
| provider | text | YES |
| token_purpose | text | YES |
| microsoft_access_token | text | YES |
| microsoft_refresh_token | text | YES |
| token_expires_at | timestamptz | YES |
| scopes | text[] | YES |
| provider_email_hash | text | YES |
| provider_display_name | text | YES |
| is_revoked | boolean | YES |
| revoked_at | timestamptz | YES |
| revoked_by | uuid | YES |
| created_at | timestamptz | NO |
| updated_at | timestamptz | NO |
