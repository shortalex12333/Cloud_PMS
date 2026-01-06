/**
 * CelesteOS Forbidden Elements
 * Source: branding/Brand/brand-refusal-list.md, branding/UX/visual-tokens.md
 *
 * This file documents what is explicitly banned from the UI.
 * Use this as a reference during code review.
 *
 * "If it feels friendly, clever, or impressive — it's wrong."
 */

// =============================================================================
// FORBIDDEN UI ELEMENTS
// =============================================================================

export const FORBIDDEN_ELEMENTS = [
  // From visual-tokens.md
  'Tooltips',
  'Info icons',
  '"Why this action exists" explanations',
  'Empty-state illustrations',
  'Success animations',
  'Gamification',
  'Chat bubbles',
  'AI avatars',
  'Confidence scores shown as percentages',
  'Auto-executed actions',

  // Decorative elements
  'Decorative icons',
  'Emotional color use',
  'Emphasis shadows',
  'Unrelated-content cards',
  'Explanatory tooltips',
] as const;

// =============================================================================
// FORBIDDEN PHRASES
// =============================================================================

export const FORBIDDEN_PHRASES = [
  // From brand-voice.md
  "I think",
  "Don't worry",
  "I recommend",
  "AI-powered",
  "Intelligent assistant",
  "Seamless",
  "Smart",
  "Easy",
  "Simple",
  "Just",
  "Working on it for you",
  "You're all set",
  "Great job",
  "Awesome",
  "Perfect",
  "Amazing",

  // Emoji/emoticons
  '🙂',
  ':)',
  '😊',
  '👍',
  '✨',
  '🎉',
] as const;

// =============================================================================
// FORBIDDEN PATTERNS
// =============================================================================

export const FORBIDDEN_PATTERNS = [
  // From brand-refusal-list.md
  'Chatbot persona in-product',
  'AI marketing theater',
  'Hidden actions (auto-execute)',
  'Assumed choices (auto-select best match)',
  'Standard SaaS design (dashboard-first)',
  'Decorative branding in UI',
  'Softened messaging',
  'Non-user focus (pretty for executives)',
  'Hybrid system (overlay to legacy)',

  // UX anti-patterns
  'READ actions opening modals',
  'MUTATE actions executing immediately',
  'Skipping any mutation ritual step',
  'Invisible uncertainty',
  'Background data mutation',
  'Success toasts',
  'Achievement unlocked patterns',
] as const;

// =============================================================================
// FORBIDDEN LUCIDE ICONS (commonly misused)
// =============================================================================

export const FORBIDDEN_ICONS = [
  // Info/Help icons (no explanations needed)
  'Info',
  'HelpCircle',
  'AlertCircle', // unless safety-critical

  // Gamification icons
  'Trophy',
  'Medal',
  'Award',
  'Star',
  'Sparkles', // unless for predictive/AI context

  // Chat/AI persona
  'Bot',
  'MessageCircle', // as chat bubble
  'MessageSquare',
  'Smile',

  // Thumbs/approval
  'ThumbsUp',
  'ThumbsDown',
  'Heart',
] as const;

// =============================================================================
// FORBIDDEN ANIMATIONS
// =============================================================================

export const FORBIDDEN_ANIMATIONS = [
  // Personality/delight
  'spin',
  'pulse',
  'bounce',
  'ping',
  'shake',
  'wiggle',
  'flash',
  'rubberBand',
  'jello',
  'heartBeat',
  'tada',
  'swing',
  'wobble',

  // Success celebrations
  'confetti',
  'fireworks',
  'celebration',
  'checkmark-pop',
  'success-bounce',

  // Loop animations
  'infinite duration animations',
  'continuous background motion',
] as const;

// =============================================================================
// FORBIDDEN COLOR USAGE
// =============================================================================

export const FORBIDDEN_COLOR_USAGE = [
  // Gradient in product UI
  'Brand gradient (#BADDE9 → #2FB9E8) in product UI',
  'Gradient backgrounds',
  'Gradient buttons',
  'Gradient cards',

  // Emotional color
  'Color for emotion (excitement, friendliness)',
  'Color for personality',
  'Random accent colors',

  // Overuse of restricted colors
  'Red for non-destructive actions',
  'Green for non-committed states',
  'Yellow/Orange for non-warnings',
] as const;

// =============================================================================
// VALIDATION HELPER
// =============================================================================

export function isTextForbidden(text: string): boolean {
  const lower = text.toLowerCase();
  return FORBIDDEN_PHRASES.some(
    (phrase) => lower.includes(phrase.toLowerCase())
  );
}

export function containsForbiddenEmoji(text: string): boolean {
  const emojiPatterns = ['🙂', ':)', '😊', '👍', '✨', '🎉', '😀', '🚀', '💪', '🙌'];
  return emojiPatterns.some((emoji) => text.includes(emoji));
}
