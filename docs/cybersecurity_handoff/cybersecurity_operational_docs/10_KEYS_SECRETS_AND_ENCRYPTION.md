# Keys, Secrets, and Encryption

## Current baseline
- TLS in transit
- Provider encryption at rest for DB/storage
- MASTER JWT verification secret used by backend

## Secrets handling rules
- No secrets in frontend env vars (NEXT_PUBLIC)
- Backend secrets only in Render environment
- Rotate secrets on schedule and on incident
- Never log secrets

## Recommended service credential split (production)
- master_membership_reader (read membership/status)
- tenant_role_reader (read auth_users_roles)
- tenant_writer (mutations)
- tenant_auditor (audit writes only)
- storage_signer (signed URL generation only)

Each credential is:
- least-privileged
- monitored
- rotated
- scoped

## Tenant-scoped encryption roadmap (future-proof)
Goal: “DB leak ≠ data leak”
Approach:
- Use envelope encryption:
  - KMS master key encrypts per-yacht DEK
  - DEK encrypts sensitive fields/documents
- Store encrypted blobs + metadata in TENANT
- Rotate DEKs per yacht without re-encrypting everything (or via staged rotation)

Pragmatic note:
This is heavy, but it’s the difference between “good SaaS” and “bank-grade”.
