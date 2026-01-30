"""
Lens Microactions Directory
============================

This directory contains lens-specific action suggestion modules.

Each lens has ONE file here that defines:
- Which entity types it handles
- Action filtering logic (state-based, role-based)
- Prefill data generation
- Priority calculation

Auto-discovered by MicroactionRegistry at startup.

Lens Files:
- part_microactions.py          # Part Lens action logic
- certificate_microactions.py   # Certificate Lens action logic
- crew_microactions.py          # Crew Lens action logic
- etc.
"""
