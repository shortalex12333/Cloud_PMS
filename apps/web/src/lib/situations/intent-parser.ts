/**
 * Query Intent Parser
 *
 * Binary classification of user queries into information or action intents.
 * No confidence scoring - deterministic rules only.
 */

import type { QueryIntent } from './types';

/**
 * Keywords that indicate an action intent
 * Note: "order" is only an action keyword at the start of the query
 */
const ACTION_KEYWORDS = [
  'create', 'add', 'mark', 'log', 'update', 'edit', 'delete',
  'generate', 'make', 'new', 'show manual', 'open manual',
  'start', 'complete', 'assign', 'schedule',
  'approve', 'reject', 'submit', 'export', 'send',
];

/**
 * Keywords that are only action indicators at the start of query
 */
const START_ACTION_KEYWORDS = ['order'];

/**
 * Classify a query as information or action intent
 *
 * @param query - User's search query
 * @returns 'information_query' | 'action_query'
 */
export function classifyIntent(query: string): QueryIntent {
  const queryLower = query.toLowerCase().trim();

  // Empty query is information
  if (!queryLower) {
    return 'information_query';
  }

  // Check for explicit action keywords
  for (const keyword of ACTION_KEYWORDS) {
    if (queryLower.includes(keyword)) {
      return 'action_query';
    }
  }

  // Check for start-only action keywords (like "order")
  for (const keyword of START_ACTION_KEYWORDS) {
    if (queryLower.startsWith(keyword)) {
      return 'action_query';
    }
  }

  // Check for imperative verb patterns at start
  const imperativePatterns = [
    /^(do|run|perform|execute|check|verify|inspect|diagnose)/,
    /^(find|get|show|view|open|display).*manual/,
  ];

  for (const pattern of imperativePatterns) {
    if (pattern.test(queryLower)) {
      return 'action_query';
    }
  }

  // Default to information query
  return 'information_query';
}

/**
 * Extract action target from an action query
 *
 * @param query - User's search query (already classified as action)
 * @returns Object with action type and target entity
 */
export function parseActionQuery(query: string): {
  actionType: string | null;
  targetEntity: string | null;
  modifier: string | null;
} {
  const queryLower = query.toLowerCase().trim();

  // Common patterns
  const patterns = [
    // "create work order for X"
    {
      regex: /^create\s+(?:work\s*order|wo)\s+for\s+(.+)/i,
      action: 'create_work_order',
    },
    // "add note to X"
    {
      regex: /^add\s+note\s+(?:to\s+)?(.+)/i,
      action: 'add_note',
    },
    // "mark X complete"
    {
      regex: /^mark\s+(.+?)\s+(?:as\s+)?complete/i,
      action: 'mark_complete',
    },
    // "show manual for X"
    {
      regex: /^(?:show|open|view)\s+manual\s+(?:for\s+)?(.+)/i,
      action: 'view_manual',
    },
    // "order part X"
    {
      regex: /^order\s+(?:part\s+)?(.+)/i,
      action: 'order_part',
    },
    // "log part usage for X"
    {
      regex: /^log\s+(?:part\s+)?usage\s+(?:for\s+)?(.+)/i,
      action: 'log_part_usage',
    },
    // "add to handover X"
    {
      regex: /^add\s+(?:to\s+)?handover\s*(.+)?/i,
      action: 'add_to_handover',
    },
    // "diagnose X"
    {
      regex: /^diagnose\s+(.+)/i,
      action: 'diagnose_fault',
    },
    // "assign X to Y"
    {
      regex: /^assign\s+(.+?)\s+to\s+(.+)/i,
      action: 'assign',
    },
  ];

  for (const { regex, action } of patterns) {
    const match = queryLower.match(regex);
    if (match) {
      return {
        actionType: action,
        targetEntity: match[1]?.trim() || null,
        modifier: match[2]?.trim() || null,
      };
    }
  }

  return {
    actionType: null,
    targetEntity: null,
    modifier: null,
  };
}

/**
 * Extract entity references from a query
 *
 * @param query - User's search query
 * @returns Array of potential entity references
 */
export function extractEntityReferences(query: string): string[] {
  const queryLower = query.toLowerCase().trim();
  const references: string[] = [];

  // Match quoted strings
  const quotedMatches = queryLower.match(/"([^"]+)"/g);
  if (quotedMatches) {
    references.push(...quotedMatches.map((m) => m.replace(/"/g, '')));
  }

  // Match work order patterns (WO-XXXX, WO#XXXX)
  const woMatches = queryLower.match(/wo[-#]?\d{4,}/gi);
  if (woMatches) {
    references.push(...woMatches);
  }

  // Match fault code patterns (F-XXXX, FAULT-XXXX)
  const faultMatches = queryLower.match(/(?:f|fault)[-#]?\d{4,}/gi);
  if (faultMatches) {
    references.push(...faultMatches);
  }

  // Match common equipment names
  const equipmentPatterns = [
    /generator\s*\d*/gi,
    /engine\s*\d*/gi,
    /pump\s*\d*/gi,
    /compressor\s*\d*/gi,
    /air\s*con(?:ditioning)?/gi,
    /watermaker/gi,
    /anchor\s*windlass/gi,
    /thruster/gi,
  ];

  for (const pattern of equipmentPatterns) {
    const matches = queryLower.match(pattern);
    if (matches) {
      references.push(...matches.map((m) => m.trim()));
    }
  }

  // Deduplicate
  return [...new Set(references)];
}

/**
 * Detect symptom codes from query
 *
 * @param query - User's search query
 * @returns Array of detected symptom codes
 */
export function detectSymptomCodes(query: string): string[] {
  const queryLower = query.toLowerCase();
  const symptoms: string[] = [];

  // Common symptom keywords mapped to codes
  const symptomMap: Record<string, string> = {
    overheat: 'OVERHEAT',
    overheating: 'OVERHEAT',
    hot: 'OVERHEAT',
    temperature: 'OVERHEAT',
    leak: 'LEAK',
    leaking: 'LEAK',
    drip: 'LEAK',
    noise: 'NOISE',
    noisy: 'NOISE',
    vibration: 'VIBRATION',
    vibrating: 'VIBRATION',
    shaking: 'VIBRATION',
    smoke: 'SMOKE',
    smoking: 'SMOKE',
    alarm: 'ALARM',
    fault: 'FAULT',
    error: 'ERROR',
    failure: 'FAILURE',
    fail: 'FAILURE',
    'not working': 'FAILURE',
    'won\'t start': 'NO_START',
    'no start': 'NO_START',
    'low pressure': 'LOW_PRESSURE',
    'high pressure': 'HIGH_PRESSURE',
    'low flow': 'LOW_FLOW',
  };

  for (const [keyword, code] of Object.entries(symptomMap)) {
    if (queryLower.includes(keyword)) {
      symptoms.push(code);
    }
  }

  return [...new Set(symptoms)];
}
