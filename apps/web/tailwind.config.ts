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
      // TYPOGRAPHY - Eloquia with system fallbacks
      // =========================================================================
      fontFamily: {
        'display': [
          'Eloquia Display',
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Display',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        'body': [
          'Eloquia Text',
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Text',
          'Segoe UI',
          'Roboto',
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
        // CelesteOS type scale
        'celeste-xs': ['0.6875rem', { lineHeight: '1.35' }],    // 11px - records
        'celeste-sm': ['0.75rem', { lineHeight: '1.5' }],       // 12px - status
        'celeste-base': ['0.8125rem', { lineHeight: '1.5' }],   // 13px - body
        'celeste-md': ['0.875rem', { lineHeight: '1.35' }],     // 14px - headers
        'celeste-lg': ['0.9375rem', { lineHeight: '1.5' }],     // 15px - emphasis
        'celeste-xl': ['1.0625rem', { lineHeight: '1.5' }],     // 17px - search
        'celeste-2xl': ['1.3125rem', { lineHeight: '1.2' }],    // 21px - titles
      },

      // =========================================================================
      // SPACING
      // =========================================================================
      spacing: {
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
        'wo-px': 'var(--wo-padding-x)',      // 32px
        'wo-py': 'var(--wo-padding-y)',      // 24px
        'wo-gap': 'var(--wo-section-gap)',   // 24px
        'wo-row': 'var(--wo-row-gap)',       // 12px
        'wo-col': 'var(--wo-column-gap)',    // 24px
      },

      // =========================================================================
      // HEIGHT - Element sizes
      // =========================================================================
      height: {
        'celeste-element-sm': '32px',
        'celeste-element-md': '40px',
        'celeste-element-lg': '48px',
        'celeste-element-xl': 'var(--celeste-height-element-xl)',  // 92px - Spotlight search bar
        'celeste-search-results': '60vh',
        // Work Order heights (from spec)
        'wo-control': 'var(--wo-control-height)',     // 36px
        'wo-nav-item': 'var(--wo-nav-item-height)',   // 40px
      },

      // =========================================================================
      // WIDTH - Layout sizes
      // =========================================================================
      width: {
        'celeste-spotlight': 'var(--celeste-spotlight-width)',  // 720px
        'celeste-panel-sm': '280px',
        'celeste-panel-medium': '320px',
        'celeste-panel-lg': '400px',
        // Work Order widths (from spec)
        'wo-container': 'var(--wo-container-width)',  // 760px
        'wo-content': 'var(--wo-max-line-width)',     // 680px
      },

      // =========================================================================
      // MAX-WIDTH - Content constraints
      // =========================================================================

      // =========================================================================
      // BORDER RADIUS
      // =========================================================================
      borderRadius: {
        // Semantic radius tokens mapped to CSS custom properties (DS-02)
        // Enables: rounded-sm, rounded-md, rounded-lg, rounded-xl, rounded-full
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        full: 'var(--radius-full)',
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
        // Enables: shadow-sm, shadow-md, shadow-lg
        // Values swap automatically between light/dark via tokens.css
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
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
      // TRANSITIONS
      // =========================================================================
      transitionDuration: {
        'celeste-fast': '100ms',
        'celeste-normal': '200ms',
        'celeste-slow': '300ms',
        'celeste-deliberate': '400ms',
      },

      transitionTimingFunction: {
        'celeste-out': 'cubic-bezier(0, 0, 0.2, 1)',
        'celeste-in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },

      // =========================================================================
      // LAYOUT
      // =========================================================================
      maxWidth: {
        'celeste-search': '680px',
        'celeste-modal': '400px',
        'celeste-modal-lg': '560px',
        'celeste-content': '1200px',
        'celeste-spotlight': 'var(--celeste-spotlight-width)',  // 720px
      },

      backdropBlur: {
        'celeste-spotlight': '72px',
        'celeste-modal': '8px',
      },
    },
  },
  plugins: [],
}

export default config
