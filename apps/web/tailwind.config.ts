import type { Config } from 'tailwindcss'

/**
 * CelesteOS Tailwind Configuration
 * Source: BRANDING_V3
 *
 * "Colour is a signal of state, not personality."
 * Maritime authority through restraint — not cheap blue saturation.
 */
const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // =========================================================================
      // COLORS - Official CelesteOS Palette
      // =========================================================================
      colors: {
        // Legacy shadcn compatibility (keep for existing components)
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },

        // =======================================================================
        // CELESTE MARITIME BRAND COLORS
        // Source: BRANDING_V3
        // =======================================================================

        // Neutral Foundation (80-90% of interface)
        celeste: {
          // Light mode backgrounds
          'white': '#EFEFF1',
          'white-soft': '#F5F5F7',
          'white-muted': '#E8E8EA',
          'white-dim': '#DCDCDE',

          // Dark mode backgrounds
          'black': '#0A0A0A',
          'black-deep': '#0B0D0F',
          'black-base': '#1A1D1F',
          'black-elevated': '#121212',
          'black-tertiary': '#1A1A1A',

          // Maritime Accent - Tonal Hierarchy
          // "Blue is not an identity wash. Blue is a precision instrument."
          'accent': '#3A7C9D',           // Primary action, selection, verified state
          'accent-hover': '#327189',     // Hover on primary actions only
          'accent-muted': 'rgba(58, 124, 157, 0.7)',   // Focus rings
          'accent-subtle': 'rgba(58, 124, 157, 0.2)',  // Selected state backgrounds
          'accent-line': 'rgba(58, 124, 157, 0.1)',    // Dividers, borders
          'accent-soft': 'rgba(58, 124, 157, 0.15)',   // Legacy compatibility

          // Semantic Text - Dark Mode (primary)
          'text-title': '#EFEFF1',
          'text-primary': '#DADDE0',
          'text-secondary': '#8A9196',
          'text-muted': '#6A6E72',
          'text-disabled': '#4A4E52',

          // Semantic Text - Light Mode
          'text-title-light': '#0B0D0F',
          'text-primary-light': '#1A1D1F',
          'text-muted-light': '#A0A4A8',
          'text-disabled-light': '#C0C4C8',

          // Semantic Backgrounds - Dark Mode
          'bg-primary': '#0A0A0A',
          'bg-secondary': '#121212',
          'bg-tertiary': '#1A1A1A',

          // Surface Depth Hierarchy - Dark Mode
          // "Variance through structure > variance through color"
          'surface': '#111316',      // Elevated cards, panels
          'panel': '#15191C',        // Nested panels, modals
          'divider': '#1E2428',      // Structural separators

          // Semantic Backgrounds - Light Mode
          'bg-primary-light': '#EFEFF1',
          'bg-secondary-light': '#E5E5E7',
          'bg-tertiary-light': '#DCDCDE',

          // Surface Depth Hierarchy - Light Mode
          'surface-light': '#FFFFFF',
          'panel-light': '#F6F7F8',
          'divider-light': '#E0E3E6',

          // Borders
          'border': '#2A2A2A',
          'border-subtle': 'rgba(255, 255, 255, 0.06)',
          'border-light': '#C8C8CA',
          'border-subtle-light': 'rgba(0, 0, 0, 0.06)',
        },

        // Restricted Colors (muted, dignified - specific contexts only)
        restricted: {
          'red': '#9D3A3A',      // Dignified warning/destructive
          'orange': '#9D6B3A',   // Muted inspection warnings
          'yellow': '#9D8A3A',   // Time-sensitive advisories
          'green': '#3A9D5C',    // Committed confirmation only
        },

        // =======================================================================
        // SEMANTIC DESIGN TOKENS — mapped to CSS custom properties
        // Source: CLAUDE.md / DS-02
        // Usage: bg-surface-base, text-txt-primary, text-brand-interactive
        // DO NOT use raw hex values. All values are var(--token-name).
        // =======================================================================
        brand: {
          ambient: 'var(--brand-ambient)',
          interactive: 'var(--brand-interactive)',
          hover: 'var(--brand-hover)',
          muted: 'var(--brand-muted)',
        },
        status: {
          critical: 'var(--status-critical)',
          'critical-bg': 'var(--status-critical-bg)',
          warning: 'var(--status-warning)',
          'warning-bg': 'var(--status-warning-bg)',
          success: 'var(--status-success)',
          'success-bg': 'var(--status-success-bg)',
          neutral: 'var(--status-neutral)',
          'neutral-bg': 'var(--status-neutral-bg)',
        },
        surface: {
          base: 'var(--surface-base)',
          primary: 'var(--surface-primary)',
          elevated: 'var(--surface-elevated)',
          hover: 'var(--surface-hover)',
          active: 'var(--surface-active)',
          border: 'var(--surface-border)',
          'border-subtle': 'var(--surface-border-subtle)',
        },
        txt: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
          disabled: 'var(--text-disabled)',
          inverse: 'var(--text-inverse)',
        },

        // =======================================================================
        // WORK ORDER - Dark Mode Tokenized Colors
        // Source: /Desktop/work_order_ux.md
        // =======================================================================
        wo: {
          'bg-main': 'var(--wo-bg-main)',
          'bg-content': 'var(--wo-bg-content)',
          'bg-sidebar': 'var(--wo-bg-sidebar)',
          'bg-highlight': 'var(--wo-bg-highlight)',
          'border': 'var(--wo-border-default)',
          'text-primary': 'var(--wo-text-primary)',
          'text-label': 'var(--wo-text-label)',
          'text-meta': 'var(--wo-text-meta)',
          'btn-primary-bg': 'var(--wo-btn-primary-bg)',
          'btn-primary-text': 'var(--wo-btn-primary-text)',
          'btn-danger-bg': 'var(--wo-btn-danger-bg)',
          'btn-danger-text': 'var(--wo-btn-danger-text)',
        },
      },

      // =========================================================================
      // TYPOGRAPHY - Per Spec Font Stack
      // ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial
      // =========================================================================
      fontFamily: {
        'sans': [
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
        'display': [
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
        'body': [
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
        'mono': [
          'SF Mono',
          'Monaco',
          'Consolas',
          'Liberation Mono',
          'monospace',
        ],
      },

      fontSize: {
        // ═══════════════════════════════════════════════════════
        // UI_SPEC.md TYPOGRAPHY SCALE — exact specification
        // Weight creates hierarchy, not size.
        // ═══════════════════════════════════════════════════════

        // Display — 28px / 700 / 1.15 / -0.02em (Lens title on mobile)
        'display': ['var(--font-size-display)', {
          lineHeight: 'var(--line-height-display)',
          letterSpacing: 'var(--letter-spacing-display)',
          fontWeight: 'var(--font-weight-display)',
        }],

        // Title — 24px / 600 / 1.2 / -0.01em (Entity name / lens title)
        'title': ['var(--font-size-title)', {
          lineHeight: 'var(--line-height-title)',
          letterSpacing: 'var(--letter-spacing-title)',
          fontWeight: 'var(--font-weight-title)',
        }],

        // Heading — 18px / 600 / 1.3 (Major section breaks)
        'heading': ['var(--font-size-heading)', {
          lineHeight: 'var(--line-height-heading)',
          letterSpacing: 'var(--letter-spacing-heading)',
          fontWeight: 'var(--font-weight-heading)',
        }],

        // Section — 14px / 600 / 1.4 (Sticky section headers)
        'section': ['var(--font-size-section)', {
          lineHeight: 'var(--line-height-section)',
          letterSpacing: 'var(--letter-spacing-section)',
          fontWeight: 'var(--font-weight-section)',
        }],

        // Body — 14px / 400 / 1.6 (Note content, descriptions)
        'body': ['var(--font-size-body)', {
          lineHeight: 'var(--line-height-body)',
          letterSpacing: 'var(--letter-spacing-body)',
          fontWeight: 'var(--font-weight-body)',
        }],

        // Label — 13px / 500 / 1.4 (Vital sign labels, form labels)
        'label': ['var(--font-size-label)', {
          lineHeight: 'var(--line-height-label)',
          letterSpacing: 'var(--letter-spacing-label)',
          fontWeight: 'var(--font-weight-label)',
        }],

        // Caption — 12px / 400 / 1.4 (Timestamps, file sizes)
        'caption': ['var(--font-size-caption)', {
          lineHeight: 'var(--line-height-caption)',
          letterSpacing: 'var(--letter-spacing-caption)',
          fontWeight: 'var(--font-weight-caption)',
        }],

        // Overline — 11px / 500 / 1.2 / 0.08em (Entity type label)
        'overline': ['var(--font-size-overline)', {
          lineHeight: 'var(--line-height-overline)',
          letterSpacing: 'var(--letter-spacing-overline)',
          fontWeight: 'var(--font-weight-overline)',
        }],

        // Action — 13px / 500 / 1 (Ghost button text, inline links)
        'action': ['var(--font-size-action)', {
          lineHeight: 'var(--line-height-action)',
          letterSpacing: 'var(--letter-spacing-action)',
          fontWeight: 'var(--font-weight-action)',
        }],

        // Legacy celeste-prefixed (keep for backward compatibility)
        'celeste-xs': ['0.6875rem', { lineHeight: '1.35' }],    // 11px
        'celeste-sm': ['0.75rem', { lineHeight: '1.5' }],       // 12px
        'celeste-base': ['0.8125rem', { lineHeight: '1.5' }],   // 13px
        'celeste-md': ['0.875rem', { lineHeight: '1.35' }],     // 14px
        'celeste-lg': ['0.9375rem', { lineHeight: '1.5' }],     // 15px
        'celeste-xl': ['1.0625rem', { lineHeight: '1.5' }],     // 17px
        'celeste-2xl': ['1.3125rem', { lineHeight: '1.2' }],    // 21px
      },

      // =========================================================================
      // SPACING (UI_SPEC.md 4px grid system)
      // =========================================================================
      spacing: {
        // UI_SPEC.md gaps
        'section': 'var(--gap-sections)',            // 24px - Between sections
        'title-vitals': 'var(--gap-title-vitals)',   // 12px - Title to vital signs
        'overline-title': 'var(--gap-overline-title)', // 4px - Overline to title
        'section-content': 'var(--gap-section-content)', // 12px - Header to content
        'vital-items': 'var(--gap-vital-items)',     // 16px - Between vital sign items

        // UI_SPEC.md component padding
        'lens-desktop': 'var(--lens-padding-desktop)', // 40px
        'lens-tablet': 'var(--lens-padding-tablet)',   // 24px
        'lens-mobile': 'var(--lens-padding-mobile)',   // 16px
        'card-x': 'var(--card-padding-x)',             // 20px
        'card-y': 'var(--card-padding-y)',             // 16px
        'modal': 'var(--modal-padding)',               // 32px
        'toast': 'var(--toast-padding)',               // 16px
        'list-row-x': 'var(--list-row-padding-x)',     // 20px
        'list-row-y': 'var(--list-row-padding-y)',     // 12px
        'input-x': 'var(--input-padding-x)',           // 12px
        'input-y': 'var(--input-padding-y)',           // 10px
        'btn-ghost-x': 'var(--button-padding-ghost-x)', // 12px
        'btn-ghost-y': 'var(--button-padding-ghost-y)', // 8px
        'btn-primary-x': 'var(--button-padding-primary-x)', // 24px
        'btn-primary-y': 'var(--button-padding-primary-y)', // 12px
        'pill-x': 'var(--pill-padding-x)',             // 12px
        'pill-y': 'var(--pill-padding-y)',             // 4px

        // Legacy celeste-prefixed
        'celeste-1': '0.25rem',   // 4px
        'celeste-2': '0.5rem',    // 8px
        'celeste-3': '0.75rem',   // 12px
        'celeste-4': '1rem',      // 16px
        'celeste-6': '1.5rem',    // 24px
        'celeste-8': '2rem',      // 32px

        // Semantic spacing tokens mapped to CSS custom properties (DS-02)
        'ds-1': 'var(--space-1)',
        'ds-2': 'var(--space-2)',
        'ds-3': 'var(--space-3)',
        'ds-4': 'var(--space-4)',
        'ds-5': 'var(--space-5)',
        'ds-6': 'var(--space-6)',
        'ds-8': 'var(--space-8)',
        'ds-10': 'var(--space-10)',
        'ds-12': 'var(--space-12)',
        'ds-16': 'var(--space-16)',
        'ds-20': 'var(--space-20)',

        // Work Order specific spacing (from spec)
        'wo-px': 'var(--wo-padding-x)',
        'wo-py': 'var(--wo-padding-y)',
        'wo-gap': 'var(--wo-section-gap)',
        'wo-row': 'var(--wo-row-gap)',
        'wo-col': 'var(--wo-column-gap)',
      },

      // =========================================================================
      // GAP - Grid/flex gaps (UI_SPEC.md exact)
      // =========================================================================
      gap: {
        'sections': 'var(--gap-sections)',           // 24px
        'title-vitals': 'var(--gap-title-vitals)',   // 12px
        'overline-title': 'var(--gap-overline-title)', // 4px
        'section-content': 'var(--gap-section-content)', // 12px
        'vital-items': 'var(--gap-vital-items)',     // 16px
      },

      // =========================================================================
      // HEIGHT - Element sizes (UI_SPEC.md proportions)
      // =========================================================================
      height: {
        // UI_SPEC.md component dimensions
        'touch': 'var(--touch-target-min)',           // 44px - Apple minimum
        'touch-mobile': 'var(--touch-target-mobile)', // 48px - Mobile minimum
        'btn-ghost': 'var(--button-height-ghost)',    // 36px
        'btn-primary': 'var(--button-height-primary)', // 40px
        'btn-icon': 'var(--button-icon-only-size)',   // 36px
        'input': 'var(--input-height)',               // 40px
        'pill': 'var(--pill-height)',                 // 24px
        'section-header': 'var(--section-header-height)', // 44px
        'list-row': 'var(--list-row-min-height)',     // 44px
        'vital-signs': 'var(--vital-signs-height)',   // 40px
        'file-preview': 'var(--file-preview-height)', // 48px
        'search': 'var(--search-height)',             // 48px
        'header': 'var(--header-height)',             // 56px
        // Legacy celeste-prefixed
        'celeste-element-sm': '32px',
        'celeste-element-md': '40px',
        'celeste-element-lg': '48px',
        'celeste-element-xl': 'var(--celeste-height-element-xl)',
        'celeste-search-results': '60vh',
        // Work Order heights (from spec)
        'wo-control': 'var(--wo-control-height)',
        'wo-nav-item': 'var(--wo-nav-item-height)',
      },

      // =========================================================================
      // MIN-HEIGHT - Touch targets and minimums (UI_SPEC.md)
      // =========================================================================
      minHeight: {
        'touch': 'var(--touch-target-min)',           // 44px
        'touch-mobile': 'var(--touch-target-mobile)', // 48px
        'list-row': 'var(--list-row-min-height)',     // 44px
      },

      // =========================================================================
      // WIDTH - Layout sizes (UI_SPEC.md proportions)
      // =========================================================================
      width: {
        // UI_SPEC.md layout proportions
        'sidebar': 'var(--sidebar-width)',            // 420px - Show Related sidebar
        'btn-icon': 'var(--button-icon-only-size)',   // 36px
        'pill-dot': 'var(--pill-dot-size)',           // 6px
        // Legacy celeste-prefixed
        'celeste-spotlight': 'var(--celeste-spotlight-width)',
        'celeste-panel-sm': '280px',
        'celeste-panel-medium': '320px',
        'celeste-panel-lg': '400px',
        // Work Order widths (from spec)
        'wo-container': 'var(--wo-container-width)',
        'wo-content': 'var(--wo-max-line-width)',
      },

      // =========================================================================
      // MAX-WIDTH - Content constraints
      // =========================================================================

      // =========================================================================
      // BORDER RADIUS
      // =========================================================================
      borderRadius: {
        // Semantic radius tokens mapped to CSS custom properties (DS-02)
        // Enables: rounded-xs, rounded-sm, rounded-md, rounded-lg, rounded-xl, rounded-full, rounded-pill
        xs: '4px',
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        full: 'var(--radius-full)',
        pill: 'var(--radius-pill)',
        // Legacy celeste-prefixed radii (keep for existing components)
        'celeste-sm': '4px',
        'celeste-md': '8px',
        'celeste-lg': '12px',
        'celeste-xl': '16px',
        'celeste-2xl': '18px',    // Spotlight panel
        // Work Order radii (from spec)
        'wo-container': 'var(--wo-radius-container)',  // 16px
        'wo-control': 'var(--wo-radius-control)',      // 10px
        'wo-close': 'var(--wo-radius-close)',          // 8px
        'wo-pill': 'var(--wo-radius-pill)',            // 6px
      },

      // =========================================================================
      // SHADOWS
      // =========================================================================
      boxShadow: {
        // Semantic shadow tokens mapped to CSS custom properties (DS-02)
        // Enables: shadow-sm, shadow-md, shadow-lg, shadow-modal
        // Values swap automatically between light/dark via tokens.css
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        modal: 'var(--modal-shadow)',
        // Legacy celeste-prefixed shadows (keep for existing components)
        'celeste-sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'celeste-md': '0 2px 4px rgba(0, 0, 0, 0.04), 0 4px 8px rgba(0, 0, 0, 0.06)',
        'celeste-lg': '0 4px 8px rgba(0, 0, 0, 0.04), 0 8px 16px rgba(0, 0, 0, 0.08)',
        'celeste-xl': '0 8px 16px rgba(0, 0, 0, 0.08), 0 24px 48px rgba(0, 0, 0, 0.16)',
        'celeste-spotlight': '0 0 0 0.5px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.04), 0 8px 16px rgba(0, 0, 0, 0.08), 0 24px 48px rgba(0, 0, 0, 0.16)',
      },

      // =========================================================================
      // ANIMATIONS - Minimal, functional only
      // =========================================================================
      keyframes: {
        'celeste-fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'celeste-spotlight-in': {
          '0%': { opacity: '0', transform: 'scale(0.98)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'celeste-slide-up': {
          '0%': { opacity: '1', transform: 'translateY(0)' },
          '100%': { opacity: '0', transform: 'translateY(-12px)' },
        },
      },

      animation: {
        'celeste-fade-in': 'celeste-fade-in 200ms ease-out forwards',
        'celeste-spotlight-in': 'celeste-spotlight-in 300ms ease-out forwards',
        'celeste-slide-up': 'celeste-slide-up 400ms ease-out',
      },

      // =========================================================================
      // TRANSITIONS (UI_SPEC.md exact specification)
      // =========================================================================
      transitionDuration: {
        // UI_SPEC.md durations
        'fast': 'var(--duration-fast)',     // 120ms - hover states
        'normal': 'var(--duration-normal)', // 200ms - toast, modal
        'slow': 'var(--duration-slow)',     // 300ms - lens transitions
        // Legacy celeste-prefixed
        'celeste-fast': '100ms',
        'celeste-normal': '200ms',
        'celeste-slow': '300ms',
        'celeste-deliberate': '400ms',
      },

      transitionTimingFunction: {
        // UI_SPEC.md easing
        'out': 'var(--ease-out)',           // cubic-bezier(0.16, 1, 0.3, 1)
        // Legacy celeste-prefixed
        'celeste-out': 'cubic-bezier(0, 0, 0.2, 1)',
        'celeste-in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },

      // =========================================================================
      // LAYOUT
      // =========================================================================
      maxWidth: {
        // UI_SPEC.md layout proportions
        'lens': 'var(--lens-max-width)',              // 800px - Lens content
        'body-text': 'var(--lens-body-max-line)',     // 680px - Readable text width
        'search': 'var(--search-max-width)',          // 720px - Search bar
        'modal': 'var(--modal-max-width)',            // 480px - Modal panel
        'toast': 'var(--toast-max-width)',            // 400px - Toast notification
        'sidebar': 'var(--sidebar-width)',            // 420px - Show Related sidebar
        // Legacy celeste-prefixed
        'celeste-search': '680px',
        'celeste-modal': '400px',
        'celeste-modal-lg': '560px',
        'celeste-content': '1200px',
        'celeste-spotlight': 'var(--celeste-spotlight-width)',
      },

      backdropBlur: {
        'celeste-spotlight': '72px',
        'celeste-modal': '8px',
        'glass': '20px',  // UI_SPEC.md glass effect
      },

      // =========================================================================
      // Z-INDEX (UI_SPEC.md layering)
      // =========================================================================
      zIndex: {
        'sticky': 'var(--z-sticky)',   // 10
        'header': 'var(--z-header)',   // 20
        'sidebar': 'var(--z-sidebar)', // 30
        'modal': 'var(--z-modal)',     // 40
        'search': 'var(--z-search)',   // 50
        'toast': 'var(--z-toast)',     // 60
      },

      // =========================================================================
      // PADDING (UI_SPEC.md responsive lens padding)
      // =========================================================================
      padding: {
        'lens-desktop': 'var(--lens-padding-desktop)', // 40px
        'lens-tablet': 'var(--lens-padding-tablet)',   // 24px
        'lens-mobile': 'var(--lens-padding-mobile)',   // 16px
        'modal': 'var(--modal-padding)',               // 32px
        'card-x': 'var(--card-padding-x)',             // 20px
        'card-y': 'var(--card-padding-y)',             // 16px
        'toast': 'var(--toast-padding)',               // 16px
        'list-row-x': 'var(--list-row-padding-x)',     // 20px
        'list-row-y': 'var(--list-row-padding-y)',     // 12px
        'input-x': 'var(--input-padding-x)',           // 12px
        'input-y': 'var(--input-padding-y)',           // 10px
        'btn-ghost-x': 'var(--button-padding-ghost-x)', // 12px
        'btn-ghost-y': 'var(--button-padding-ghost-y)', // 8px
        'btn-primary-x': 'var(--button-padding-primary-x)', // 24px
        'btn-primary-y': 'var(--button-padding-primary-y)', // 12px
        'pill-x': 'var(--pill-padding-x)',             // 12px
        'pill-y': 'var(--pill-padding-y)',             // 4px
      },
    },
  },
  plugins: [],
}

export default config
