# Cybersecurity Pack (Production-Grade) — Celeste MASTER/TENANT + Action Router

Version: v2 (2026-01-28)

This bundle is intentionally **dense**. It's meant to survive:
- CISO review (controls + threat model + failure modes)
- SOC 2 Type II evidence design
- ISO 27001 narrative and Annex A mapping
- Legal scrutiny in the event of a breach claim

## How to use
1. Start with `01_EXEC_SUMMARY.md`
2. Review architecture + trust boundaries in `02_ARCHITECTURE_CURRENT.md`
3. Review threat model in `03_THREAT_MODEL_CISO.md`
4. Implement guardrails and workflows in `04_GUARDRAILS_AND_GATES.md` + `05_ACCESS_LIFECYCLE.md`
5. Apply Action Router contract in `06_ACTION_ROUTER_SPEC.md`
6. Pay special attention to streaming search controls in `07_STREAMING_SEARCH_SECURITY.md`
7. Use production checklists in `12_PRODUCTION_READINESS.md`
8. Keep roadmap honest in `13_ROADMAP_AND_FUTUREPROOF.md`

## Non-negotiable principle (because your risk is $50m/yacht)
No single bug, human mistake, or misconfiguration should be able to produce
cross-yacht disclosure of classified data. Achieve this with **defense in depth**:
- Control plane gating (MASTER membership/status)
- Execution boundary (Action Router)
- Data plane enforcement (yacht_id + RLS + storage path policies)
- Observability + alerting
- (Roadmap) cryptographic tenant isolation

## Files
See `MANIFEST.md`.
