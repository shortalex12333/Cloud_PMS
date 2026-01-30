"""
Lens Capabilities Directory
============================

This directory contains lens-specific search capability modules.

Each lens has ONE file here that defines:
- Entity-to-capability mappings
- Search query implementations
- Result formatting

Auto-discovered by CapabilityRegistry at startup.

Lens Files:
- part_capabilities.py          # Part Lens (inventory, parts, shopping list)
- certificate_capabilities.py   # Certificate Lens (vessel/crew certificates)
- crew_capabilities.py          # Crew Lens (personnel, roles, qualifications)
- work_order_capabilities.py    # Work Order Lens (maintenance tasks)
- document_capabilities.py      # Document Lens (manuals, procedures)
- equipment_capabilities.py     # Equipment Lens (machinery, systems)
- fault_capabilities.py         # Fault Lens (diagnostics, error codes)

To add a new lens:
1. Create {lens_name}_capabilities.py
2. Subclass BaseLensCapability
3. Implement get_entity_mappings() and execute_capability()
4. Restart server → Auto-discovered and validated
"""
