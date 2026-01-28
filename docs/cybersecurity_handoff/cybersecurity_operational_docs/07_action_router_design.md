# Action Router Design Implications

## Do we need a new Action Router per action?
No.

Use:
- One Action Router
- Multiple action groups (READ, MUTATE, SIGNED, ADMIN)

Each action declares:
- Required role(s)
- Required approval level
- Required signatures

Router responsibilities:
- Validate identity
- Validate membership
- Validate role
- Validate resource ownership
- Enforce approvals
- Execute intent

This mirrors patterns used in banking and defence systems.
