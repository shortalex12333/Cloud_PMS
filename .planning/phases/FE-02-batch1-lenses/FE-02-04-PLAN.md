---
wave: 1
depends_on: []
files_modified:
  - apps/web/src/components/lens/CertificateLens.tsx
  - apps/web/src/app/certificates/[id]/page.tsx
autonomous: true
requirements: [CERT-03]
---

# Plan FE-02-04: Certificate Lens Rebuild

## Objective

Rebuild Certificate lens to Work Order standard: LensHeader, VitalSignsRow with 5 indicators (status, type, expiry date, issuing authority, linked entity), section containers (Details, Linked Documents, Renewal History), full-screen layout.

## Tasks

<task id="1">
Create CertificateLens.tsx:

```tsx
interface CertificateLensProps {
  certificate: CertificateData;
  certificateType: 'vessel' | 'crew';
  onBack?: () => void;
  onClose: () => void;
}
```

VitalSignsRow with 5 signs:
- Status (valid/expiring/expired) - StatusPill with color mapping
- Type (certificate type name)
- Expiry ("Expires Jan 23, 2026" or "Expired 5 days ago") - warning/critical color
- Issuing Authority
- Linked Entity (vessel name or crew member name) - EntityLink
</task>

<task id="2">
Create certificate-specific sections:

- **DetailsSection** - Certificate number, issue date, expiry date, issuing authority, notes
- **LinkedDocumentsSection** - Scanned certificate, supporting documents
- **RenewalHistorySection** - Previous versions, superseded certificates

All sections use SectionContainer with stickyTop={56}.
</task>

<task id="3">
Create useCertificateActions hook:

Actions:
- view_certificate
- create_certificate
- update_certificate
- find_expiring_certificates
- link_document
- supersede_certificate

Role-based visibility.
</task>

<task id="4">
Wire certificates/[id]/page.tsx:

1. Determine certificate type (vessel vs crew)
2. Fetch certificate data
3. Render CertificateLens
4. Handle navigation
5. Log to ledger
</task>

<task id="5">
Build verification:

```bash
cd apps/web && npm run build
```
</task>

## Verification

```bash
cd apps/web && npm run build
ls apps/web/src/components/lens/CertificateLens.tsx
```

## must_haves

- [ ] CertificateLens.tsx supports both vessel and crew certificates
- [ ] VitalSignsRow with expiry indicator (warning/critical colors)
- [ ] Linked Documents section
- [ ] Renewal History section
- [ ] useCertificateActions hook
- [ ] Build passes
