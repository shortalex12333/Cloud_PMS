/**
 * Document Classification Utility
 *
 * Classifies documents as operational vs compliance to determine
 * visibility rules for "Add to Handover" action.
 *
 * Per Document Situation View.md:
 * - Operational docs: Add to Handover visible by default
 * - Compliance docs: Add to Handover hidden in dropdown menu
 */

import type { DocumentClassification } from '@/types/situation';

// ============================================================================
// CLASSIFICATION KEYWORDS
// ============================================================================

/**
 * Keywords that indicate operational/informational documents
 */
const OPERATIONAL_KEYWORDS = [
  // Manuals
  'manual',
  'guide',
  'handbook',
  'instruction',
  'procedure',
  'sop',
  'standard operating procedure',

  // Troubleshooting
  'troubleshooting',
  'diagnostic',
  'fault finding',
  'repair',
  'maintenance',

  // Technical
  'technical',
  'specifications',
  'spec sheet',
  'datasheet',
  'schematic',
  'diagram',
  'drawing',

  // Safety & Operations
  'safety note',
  'warning',
  'precaution',
  'operating',
  'operation',
  'user guide',

  // Internal
  'internal',
  'reference',
  'notes',
  'log',
  'checklist',
];

/**
 * Keywords that indicate compliance/authority documents
 */
const COMPLIANCE_KEYWORDS = [
  // Certificates
  'certificate',
  'certification',
  'certified',

  // Regulatory
  'regulatory',
  'compliance',
  'regulation',
  'class',
  'classification',

  // Approvals & Licenses
  'approval',
  'approved',
  'license',
  'licence',
  'permit',
  'authorization',

  // Inspections
  'inspection',
  'survey',
  'audit',
  'verification',

  // Legal
  'legal',
  'statutory',
  'mandatory',

  // Specific document types
  'load line',
  'tonnage',
  'registry',
  'flag state',
  'port state',
  'insurance',
  'policy',
];

/**
 * Compliance document patterns (stronger signals)
 */
const COMPLIANCE_PATTERNS = [
  /certificate of/i,
  /class approval/i,
  /regulatory compliance/i,
  /inspection report/i,
  /survey report/i,
  /flag state/i,
  /port state/i,
  /statutory/i,
  /load line/i,
  /tonnage certificate/i,
  /insurance certificate/i,
];

// ============================================================================
// CLASSIFICATION FUNCTIONS
// ============================================================================

/**
 * Classify document based on title and metadata
 *
 * @param title - Document title
 * @param metadata - Optional document metadata (source, category, etc.)
 * @returns DocumentClassification
 */
export function classifyDocument(
  title: string,
  metadata?: Record<string, any>
): DocumentClassification {
  const normalizedTitle = title.toLowerCase();
  const source = metadata?.source?.toLowerCase() || '';
  const category = metadata?.category?.toLowerCase() || '';

  // Check for strong compliance patterns first
  for (const pattern of COMPLIANCE_PATTERNS) {
    if (pattern.test(title)) {
      return 'compliance';
    }
  }

  // Check source/category metadata
  if (source.includes('regulatory') || source.includes('class') || source.includes('flag')) {
    return 'compliance';
  }

  if (category.includes('certificate') || category.includes('compliance') || category.includes('regulatory')) {
    return 'compliance';
  }

  // Score keywords
  let operationalScore = 0;
  let complianceScore = 0;

  for (const keyword of OPERATIONAL_KEYWORDS) {
    if (normalizedTitle.includes(keyword) || source.includes(keyword) || category.includes(keyword)) {
      operationalScore++;
    }
  }

  for (const keyword of COMPLIANCE_KEYWORDS) {
    if (normalizedTitle.includes(keyword) || source.includes(keyword) || category.includes(keyword)) {
      complianceScore++;
    }
  }

  // Compliance keywords have higher weight
  if (complianceScore > 0) {
    return 'compliance';
  }

  // Default to operational if any operational keywords found
  if (operationalScore > 0) {
    return 'operational';
  }

  // Default fallback: operational (safer for user workflow)
  return 'operational';
}

/**
 * Determine if "Add to Handover" should be immediately visible
 *
 * @param classification - Document classification
 * @returns true if button should be visible, false if dropdown-only
 */
export function shouldShowAddToHandoverButton(classification: DocumentClassification): boolean {
  return classification === 'operational';
}

/**
 * Get document classification display label
 */
export function getClassificationLabel(classification: DocumentClassification): string {
  return classification === 'operational' ? 'Operational Document' : 'Compliance Document';
}

/**
 * Get document classification icon
 */
export function getClassificationIcon(classification: DocumentClassification): string {
  return classification === 'operational' ? '📖' : '🔒';
}

/**
 * Batch classify multiple documents
 */
export function classifyDocuments(
  documents: Array<{ title: string; metadata?: Record<string, any> }>
): Array<{ title: string; classification: DocumentClassification }> {
  return documents.map(doc => ({
    title: doc.title,
    classification: classifyDocument(doc.title, doc.metadata),
  }));
}
