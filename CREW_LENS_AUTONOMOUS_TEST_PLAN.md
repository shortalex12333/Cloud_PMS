# Crew Lens Autonomous Testing Plan
**Date:** 2026-01-30
**Scope:** Comprehensive entity extraction pipeline validation
**Status:** IN PROGRESS

---

## Test Categories

### 1. Entity Extraction Pipeline Tests
- [ ] Test REST_COMPLIANCE entity extraction with chaotic input
- [ ] Test WARNING_SEVERITY entity extraction with misspellings
- [ ] Test WARNING_STATUS entity extraction with paraphrases
- [ ] Test vague input handling
- [ ] Test entity extraction coverage (gazetteer vs AI path)
- [ ] Test async pipeline performance

### 2. Capability Mapping Tests
- [ ] Verify entity types map to correct capabilities
- [ ] Verify capabilities are ACTIVE (not blocked)
- [ ] Verify search columns match table schema
- [ ] Test multi-entity queries
- [ ] Test invalid entity types are skipped

### 3. Backend Search Execution Tests
- [ ] Test crew_hours_of_rest_search capability execution
- [ ] Test crew_warnings_search capability execution
- [ ] Test RLS enforcement (crew can only see own records)
- [ ] Test RLS enforcement (HOD sees department crew only)
- [ ] Test RLS enforcement (Captain sees all departments)

### 4. Microaction Surfacing Tests
- [ ] Test available actions surface in search results
- [ ] Test role-based action filtering
- [ ] Test action buttons can be rendered on frontend
- [ ] Test action metadata is correct

### 5. Natural Language Query Tests (Chaotic/Vague Input)
- [ ] "show warnings" (vague - which type?)
- [ ] "crew rest violations" (paraphrase)
- [ ] "criticla warrnings" (misspelling)
- [ ] "people who didnt sleep enuf" (very vague, misspelled)
- [ ] "high severity active warnings deck crew" (complex, multi-entity)

### 6. Integration Tests
- [ ] Test complete pipeline: query → extraction → capability → search → results
- [ ] Test frontend entity type translation
- [ ] Test async performance benchmarks

---

## Test Execution Log

### Phase 1: Entity Extraction Pipeline (ASYNC)
Status: STARTING

