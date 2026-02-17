/**
 * CelesteOS Spacing System
 * Source: branding/UX/visual-tokens.md
 *
 * Spacing serves structure and hierarchy, never decoration.
 * Consistent spacing creates predictability under fatigue.
 */

// =============================================================================
// BASE SCALE (4px grid)
// =============================================================================

export const spacing = {
  0: '0',
  px: '1px',
  0.5: '0.125rem',  // 2px
  1: '0.25rem',     // 4px
  1.5: '0.375rem',  // 6px
  2: '0.5rem',      // 8px
  2.5: '0.625rem',  // 10px
  3: '0.75rem',     // 12px
  3.5: '0.875rem',  // 14px
  4: '1rem',        // 16px
  5: '1.25rem',     // 20px
  6: '1.5rem',      // 24px
  7: '1.75rem',     // 28px
  8: '2rem',        // 32px
  9: '2.25rem',     // 36px
  10: '2.5rem',     // 40px
  12: '3rem',       // 48px
  14: '3.5rem',     // 56px
  16: '4rem',       // 64px
  20: '5rem',       // 80px
  24: '6rem',       // 96px
} as const;

// =============================================================================
// COMPONENT-SPECIFIC SPACING
// =============================================================================

export const componentSpacing = {
  // Search bar - ChatGPT-style pill
  searchPaddingX: spacing[5],        // 20px
  searchPaddingY: spacing[2.5],      // 10px
  searchHeight: '56px',
  searchMaxWidth: '760px',
  searchRadius: '999px',             // Full pill radius

  // Search bar controls
  searchBtnSize: '36px',
  searchBtnIconSize: '18px',
  searchBtnGap: spacing[2],          // 8px

  // Secondary search surface
  searchSecondaryHeight: '48px',
  searchSecondaryRadius: '24px',
  searchSecondaryGap: spacing[2],    // 8px

  // Utility row
  searchUtilityGap: spacing[4],      // 16px
  searchUtilityIconSize: '20px',
  searchUtilityBtnPadding: spacing[2.5], // 10px

  // Result cards
  cardPaddingX: spacing[4],          // 16px
  cardPaddingY: spacing[3],          // 12px
  cardGap: spacing[1.5],             // 6px between elements

  // Result rows (compact)
  rowPaddingX: spacing[2.5],         // 10px
  rowPaddingY: spacing[1.5],         // 6px
  rowGap: spacing[3],                // 12px between icon and content

  // Dropdown
  dropdownPaddingX: spacing[3],      // 12px
  dropdownPaddingY: spacing[1.5],    // 6px per item
  dropdownMinWidth: '160px',

  // Actions
  actionGap: spacing[2],             // 8px between actions
  actionPadding: spacing[1],         // 4px touch target padding

  // Entity/Status lines
  entityPaddingX: spacing[4],        // 16px
  entityPaddingY: spacing[2],        // 8px

  // Modals
  modalPadding: spacing[6],          // 24px
  modalMaxWidth: '400px',
  modalGap: spacing[4],              // 16px between sections
} as const;

// =============================================================================
// LAYOUT SPACING
// =============================================================================

export const layout = {
  // Page
  pageMaxWidth: '760px',             // Updated for ChatGPT-style search bar
  pagePaddingX: spacing[4],          // 16px on mobile
  pageTopOffset: '18vh',             // Spotlight position from top

  // Viewport
  mobileBreakpoint: '640px',
  tabletBreakpoint: '768px',
  desktopBreakpoint: '1024px',
} as const;

// =============================================================================
// ICON SIZES
// =============================================================================

export const iconSize = {
  xs: '12px',   // Inline indicators
  sm: '14px',   // Action icons
  md: '16px',   // Standard UI
  lg: '20px',   // Search icon
  xl: '24px',   // Primary actions
  '2xl': '32px', // App icons in results
} as const;

// =============================================================================
// BORDER RADIUS
// =============================================================================

export const radius = {
  none: '0',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '18px',  // Legacy spotlight panel
  '3xl': '24px',  // Secondary surfaces
  full: '9999px', // Pills, circular buttons, ChatGPT-style search bar
} as const;

// =============================================================================
// CSS CUSTOM PROPERTIES
// =============================================================================

export const cssVars = {
  '--spacing-1': spacing[1],
  '--spacing-2': spacing[2],
  '--spacing-3': spacing[3],
  '--spacing-4': spacing[4],
  '--spacing-6': spacing[6],
  '--spacing-8': spacing[8],

  '--radius-sm': radius.sm,
  '--radius-md': radius.md,
  '--radius-lg': radius.lg,
  '--radius-xl': radius.xl,
  '--radius-2xl': radius['2xl'],
  '--radius-3xl': radius['3xl'],
  '--radius-full': radius.full,

  '--page-max-width': layout.pageMaxWidth,
  '--page-top-offset': layout.pageTopOffset,

  // Search bar tokens
  '--search-height': componentSpacing.searchHeight,
  '--search-max-width': componentSpacing.searchMaxWidth,
  '--search-radius': componentSpacing.searchRadius,
  '--search-btn-size': componentSpacing.searchBtnSize,
  '--search-secondary-height': componentSpacing.searchSecondaryHeight,
} as const;
