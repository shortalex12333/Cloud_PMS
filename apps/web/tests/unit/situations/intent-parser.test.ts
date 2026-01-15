/**
 * Intent Parser Unit Tests
 *
 * Tests for query intent classification and entity extraction.
 */

import { describe, it, expect } from 'vitest';
import {
  classifyIntent,
  parseActionQuery,
  extractEntityReferences,
  detectSymptomCodes,
} from '@/lib/situations/intent-parser';

describe('Intent Parser', () => {
  // ============================================================================
  // classifyIntent Tests
  // ============================================================================

  describe('classifyIntent', () => {
    it('should classify empty query as information', () => {
      expect(classifyIntent('')).toBe('information_query');
      expect(classifyIntent('   ')).toBe('information_query');
    });

    it('should classify "create" queries as action', () => {
      expect(classifyIntent('create work order')).toBe('action_query');
      expect(classifyIntent('create new fault report')).toBe('action_query');
    });

    it('should classify "add" queries as action', () => {
      expect(classifyIntent('add note')).toBe('action_query');
      expect(classifyIntent('add to handover')).toBe('action_query');
      expect(classifyIntent('add part')).toBe('action_query');
    });

    it('should classify "mark" queries as action', () => {
      expect(classifyIntent('mark complete')).toBe('action_query');
      expect(classifyIntent('mark as done')).toBe('action_query');
    });

    it('should classify "show manual" as action', () => {
      expect(classifyIntent('show manual for generator')).toBe('action_query');
      expect(classifyIntent('open manual')).toBe('action_query');
    });

    it('should classify status queries as information', () => {
      expect(classifyIntent('generator 2 status')).toBe('information_query');
      expect(classifyIntent('what is the status')).toBe('information_query');
    });

    it('should classify history queries as information', () => {
      expect(classifyIntent('MTU overheating history')).toBe('information_query');
      expect(classifyIntent('work order history')).toBe('information_query');
    });

    it('should classify parts queries as information', () => {
      expect(classifyIntent('what parts needed')).toBe('information_query');
      expect(classifyIntent('parts for generator')).toBe('information_query');
    });

    it('should classify equipment names as information', () => {
      expect(classifyIntent('generator 1')).toBe('information_query');
      expect(classifyIntent('main engine')).toBe('information_query');
    });

    it('should classify "order" as action', () => {
      expect(classifyIntent('order part')).toBe('action_query');
      expect(classifyIntent('order filter')).toBe('action_query');
    });

    it('should classify "schedule" as action', () => {
      expect(classifyIntent('schedule inspection')).toBe('action_query');
      expect(classifyIntent('schedule maintenance')).toBe('action_query');
    });

    it('should be case insensitive', () => {
      expect(classifyIntent('CREATE WORK ORDER')).toBe('action_query');
      expect(classifyIntent('Add Note')).toBe('action_query');
    });
  });

  // ============================================================================
  // parseActionQuery Tests
  // ============================================================================

  describe('parseActionQuery', () => {
    it('should parse "create work order for X"', () => {
      const result = parseActionQuery('create work order for generator 2');
      expect(result.actionType).toBe('create_work_order');
      expect(result.targetEntity).toBe('generator 2');
    });

    it('should parse "add note to X"', () => {
      const result = parseActionQuery('add note to fault F-123');
      expect(result.actionType).toBe('add_note');
      expect(result.targetEntity).toBe('fault f-123');
    });

    it('should parse "mark X complete"', () => {
      const result = parseActionQuery('mark WO-456 complete');
      expect(result.actionType).toBe('mark_complete');
      expect(result.targetEntity).toBe('wo-456');
    });

    it('should parse "show manual for X"', () => {
      const result = parseActionQuery('show manual for watermaker');
      expect(result.actionType).toBe('view_manual');
      expect(result.targetEntity).toBe('watermaker');
    });

    it('should parse "order part X"', () => {
      const result = parseActionQuery('order part oil filter');
      expect(result.actionType).toBe('order_part');
      expect(result.targetEntity).toBe('oil filter');
    });

    it('should parse "diagnose X"', () => {
      const result = parseActionQuery('diagnose overheating issue');
      expect(result.actionType).toBe('diagnose_fault');
      expect(result.targetEntity).toBe('overheating issue');
    });

    it('should return nulls for non-matching queries', () => {
      const result = parseActionQuery('generator status');
      expect(result.actionType).toBeNull();
      expect(result.targetEntity).toBeNull();
    });
  });

  // ============================================================================
  // extractEntityReferences Tests
  // ============================================================================

  describe('extractEntityReferences', () => {
    it('should extract quoted strings', () => {
      const refs = extractEntityReferences('search for "Main Engine Generator 1"');
      expect(refs).toContain('main engine generator 1');
    });

    it('should extract work order patterns', () => {
      const refs = extractEntityReferences('WO-1234 needs attention');
      expect(refs.some((r) => r.toLowerCase().includes('wo'))).toBe(true);
    });

    it('should extract fault code patterns', () => {
      const refs = extractEntityReferences('check fault F-5678');
      expect(refs.some((r) => r.toLowerCase().includes('f-5678'))).toBe(true);
    });

    it('should extract generator references', () => {
      const refs = extractEntityReferences('generator 2 overheating');
      expect(refs.some((r) => r.includes('generator'))).toBe(true);
    });

    it('should extract engine references', () => {
      const refs = extractEntityReferences('main engine noise');
      expect(refs.some((r) => r.includes('engine'))).toBe(true);
    });

    it('should extract pump references', () => {
      const refs = extractEntityReferences('bilge pump 1 not working');
      expect(refs.some((r) => r.includes('pump'))).toBe(true);
    });

    it('should extract watermaker references', () => {
      const refs = extractEntityReferences('watermaker maintenance');
      expect(refs).toContain('watermaker');
    });

    it('should extract air conditioning references', () => {
      const refs = extractEntityReferences('air conditioning problem');
      expect(refs.some((r) => r.includes('air con'))).toBe(true);
    });

    it('should deduplicate references', () => {
      const refs = extractEntityReferences('generator 1 and generator 1');
      const generatorRefs = refs.filter((r) => r.includes('generator'));
      expect(generatorRefs.length).toBe(1);
    });

    it('should return empty array for query with no entities', () => {
      const refs = extractEntityReferences('how do I');
      expect(refs).toHaveLength(0);
    });
  });

  // ============================================================================
  // detectSymptomCodes Tests
  // ============================================================================

  describe('detectSymptomCodes', () => {
    it('should detect OVERHEAT symptom', () => {
      expect(detectSymptomCodes('generator overheating')).toContain('OVERHEAT');
      expect(detectSymptomCodes('engine is hot')).toContain('OVERHEAT');
      expect(detectSymptomCodes('high temperature')).toContain('OVERHEAT');
    });

    it('should detect LEAK symptom', () => {
      expect(detectSymptomCodes('oil leak detected')).toContain('LEAK');
      expect(detectSymptomCodes('pipe is leaking')).toContain('LEAK');
      expect(detectSymptomCodes('drip from pump')).toContain('LEAK');
    });

    it('should detect NOISE symptom', () => {
      expect(detectSymptomCodes('strange noise from engine')).toContain('NOISE');
      expect(detectSymptomCodes('pump is noisy')).toContain('NOISE');
    });

    it('should detect VIBRATION symptom', () => {
      expect(detectSymptomCodes('excessive vibration')).toContain('VIBRATION');
      expect(detectSymptomCodes('engine vibrating')).toContain('VIBRATION');
      expect(detectSymptomCodes('shaft shaking')).toContain('VIBRATION');
    });

    it('should detect SMOKE symptom', () => {
      expect(detectSymptomCodes('smoke from exhaust')).toContain('SMOKE');
      expect(detectSymptomCodes('engine smoking')).toContain('SMOKE');
    });

    it('should detect ALARM symptom', () => {
      expect(detectSymptomCodes('alarm triggered')).toContain('ALARM');
    });

    it('should detect FAILURE symptom', () => {
      expect(detectSymptomCodes('pump failure')).toContain('FAILURE');
      expect(detectSymptomCodes('system fail')).toContain('FAILURE');
      expect(detectSymptomCodes('not working')).toContain('FAILURE');
    });

    it('should detect NO_START symptom', () => {
      expect(detectSymptomCodes("won't start")).toContain('NO_START');
      expect(detectSymptomCodes('no start')).toContain('NO_START');
    });

    it('should detect multiple symptoms', () => {
      const symptoms = detectSymptomCodes('engine overheating and making noise');
      expect(symptoms).toContain('OVERHEAT');
      expect(symptoms).toContain('NOISE');
    });

    it('should return empty array for no symptoms', () => {
      const symptoms = detectSymptomCodes('generator 1 status');
      expect(symptoms).toHaveLength(0);
    });

    it('should deduplicate symptom codes', () => {
      const symptoms = detectSymptomCodes('overheating overheat hot temperature');
      const overheatCount = symptoms.filter((s) => s === 'OVERHEAT').length;
      expect(overheatCount).toBe(1);
    });
  });
});
