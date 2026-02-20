/**
 * fileUtils.ts — File type detection and formatting utilities.
 *
 * Per UI_SPEC.md decision: getAttachmentKind uses extension set, not MIME type
 * (MIME unreliable from signed storage URLs). getFileCategory uses MIME type
 * as primary signal for typed file objects where MIME is available.
 */

// ============================================================================
// CONSTANTS
// ============================================================================

/** Image MIME type prefix */
const IMAGE_MIME_PREFIX = 'image/';

/** Video MIME type prefix */
const VIDEO_MIME_PREFIX = 'video/';

/** Media file extensions per UI_SPEC.md */
const IMAGE_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.heic', '.webp',
]);

const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm']);

const MEDIA_EXTENSIONS = new Set([
  ...IMAGE_EXTENSIONS,
  ...VIDEO_EXTENSIONS,
]);

// ============================================================================
// FILE CATEGORY
// ============================================================================

/**
 * Determine the category of a file from its MIME type.
 *
 * Used when a typed file object is available (mime_type is reliable).
 */
export function getFileCategory(mimeType: string): 'image' | 'video' | 'document' {
  if (mimeType.startsWith(IMAGE_MIME_PREFIX)) return 'image';
  if (mimeType.startsWith(VIDEO_MIME_PREFIX)) return 'video';
  return 'document';
}

/**
 * Broad media vs document kind from filename extension.
 *
 * Consistent with existing getAttachmentKind in AttachmentsSection.
 */
export function getAttachmentKind(filename: string): 'media' | 'document' {
  const ext = ('.' + filename.split('.').pop()?.toLowerCase()) as string;
  if (MEDIA_EXTENSIONS.has(ext)) return 'media';
  return 'document';
}

// ============================================================================
// FILE SIZE FORMATTING
// ============================================================================

/**
 * Format file size in bytes to a human-readable string.
 *
 * Examples:
 * - 512 → "512 B"
 * - 2048 → "2.0 KB"
 * - 1572864 → "1.5 MB"
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ============================================================================
// DOCUMENT ICON
// ============================================================================

/**
 * Get document icon character based on file extension.
 *
 * Per UI_SPEC.md: 📄 for PDF, 📝 for DOCX, 📊 for spreadsheets, 📑 for PPT.
 */
export function getDocumentIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return '📄';
    case 'xlsx':
    case 'xls':
    case 'csv':
      return '📊';
    case 'docx':
    case 'doc':
      return '📝';
    case 'pptx':
    case 'ppt':
      return '📑';
    default:
      return '📎';
  }
}
