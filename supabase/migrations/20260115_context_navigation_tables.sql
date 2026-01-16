-- Context Navigation Tables (Situational Continuity Layer)
-- =========================================================
-- PLACEHOLDER - Will implement in Phase 4
--
-- This is DISTINCT from situation_detections (existing fault pattern detection system).
-- This handles navigation context, related expansion, and audit logging.
--
-- Based on spec: /docs/15_situational_continuity_layer/30_contracts/30_DATABASE_SCHEMA_ASSUMPTIONS.md

-- TODO: Create navigation_contexts table
-- TODO: Create user_added_relations table
-- TODO: Create audit_events table (if not exists)
-- TODO: Add RLS policies for yacht isolation
-- TODO: Add indexes for performance
-- TODO: Create helper functions for deterministic related queries

-- CRITICAL: NO vector search, NO embeddings, NO LLM calls in related expansion
-- All related queries must use JOIN/FK or user_added_relations only

-- Migration will be executed in Phase 4 after backend implementation is complete
