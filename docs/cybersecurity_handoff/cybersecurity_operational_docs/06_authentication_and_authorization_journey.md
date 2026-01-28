# Authentication & Authorization Journey

1. User authenticates against MASTER.
2. JWT issued (no tenant data embedded by default).
3. Backend middleware:
   - Verifies JWT
   - Resolves active membership
   - Resolves yacht_id
   - Resolves yacht-specific role from TENANT
4. Action Router validates intent + role.
5. Handler executes with explicit yacht_id.
6. Audit log written.

Key rule:
Tenant context is never inferred from client input.
