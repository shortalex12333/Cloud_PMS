# Threat Model Summary

Primary risk: cross-yacht disclosure.
Defense-in-depth layers:
1) MASTER membership gating
2) Action Router execution boundary
3) Explicit yacht_id in code + RLS backstop
4) Storage path enforcement
5) Monitoring + incident response
6) Roadmap: tenant-scoped encryption keys
