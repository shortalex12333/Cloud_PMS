-- Migration 009: Drop Empty Search Tables
-- Purpose: Clean up dead/unused tables that add schema confusion
-- All have 0 rows as of 2026-02-05

-- ============================================================================
-- Source tables (never populated)
-- ============================================================================
DROP TABLE IF EXISTS search_manual_embeddings CASCADE;
DROP TABLE IF EXISTS search_ocred_pages CASCADE;

-- ============================================================================
-- Analytics tables (never wired up)
-- ============================================================================
DROP TABLE IF EXISTS search_clicks CASCADE;
DROP TABLE IF EXISTS search_query_logs CASCADE;
DROP TABLE IF EXISTS search_sessions CASCADE;
DROP TABLE IF EXISTS search_suggestions CASCADE;
DROP TABLE IF EXISTS search_suggestion_analytics CASCADE;
DROP TABLE IF EXISTS search_symptom_reports CASCADE;

-- Done. 8 empty tables removed.
