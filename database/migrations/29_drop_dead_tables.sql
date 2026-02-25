-- Migration: Drop dead tables
-- These tables are no longer used by the application and can be safely removed

DROP TABLE IF EXISTS audit_events;
DROP TABLE IF EXISTS document_sections;
DROP TABLE IF EXISTS equipment_status_log;
DROP TABLE IF EXISTS navigation_contexts;
DROP TABLE IF EXISTS predictive_state;
DROP TABLE IF EXISTS situation_detections;
DROP TABLE IF EXISTS suggestion_log;
DROP TABLE IF EXISTS symptom_reports;
DROP TABLE IF EXISTS user_tokens;
DROP TABLE IF EXISTS action_executions;
DROP TABLE IF EXISTS equipment_hours_log;
