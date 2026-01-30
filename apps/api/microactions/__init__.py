"""
Microactions Module
===================

Adds context-valid action suggestions to search results.

Flow:
1. Search results returned from SQL RAG
2. For each result, microaction module determines valid actions
3. Actions filtered by entity state, user role, query intent
4. Enriched results sent to frontend

Components:
- base_microaction.py: Base classes for lens microactions
- microaction_registry.py: Auto-discovery and management
- lens_microactions/: Lens-specific action logic
"""
