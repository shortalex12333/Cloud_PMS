# Customer-Facing Security Posture (Conservative, Defensible)

Celeste uses a control-plane/data-plane architecture to limit blast radius:
- Identity and membership are managed centrally.
- Yacht operational data is stored separately and accessed only via server-side services.
- Tenant isolation is enforced through explicit tenant identifiers, role-based access controls,
  and database/storage policies.

Security-relevant actions are logged and auditable. Access is least-privilege by default,
and administrative workflows are controlled and reviewed.

Encryption is used in transit and at rest. Additional tenant-scoped encryption controls are
available on a roadmap and may be offered for high-classification deployments.

Celeste maintains documented incident response procedures, including the ability to rapidly
revoke access and suspend operations for containment.
