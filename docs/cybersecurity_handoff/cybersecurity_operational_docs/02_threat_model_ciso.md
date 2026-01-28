# CISO-Grade Threat Model

## Assets
- Yacht operational data (highly classified)
- Crew identities and roles
- Audit logs
- Encryption keys

## Threat Actors
- External attackers
- Malicious insiders
- Compromised services
- Operational mistakes

## Key Principle
No single failure should cause cross-tenant data exposure.

## Defence-in-Depth Layers
1. Identity & membership control (MASTER)
2. Execution boundary (Action Router)
3. Logical isolation (yacht_id + RLS)
4. Audit, monitoring, detection
5. Cryptographic isolation (roadmap)
