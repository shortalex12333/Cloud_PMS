import type { Config } from 'tailwindcss'

/**
 * CelesteOS Tailwind Configuration
 * Source: branding/Brand/colour-system.md, branding/Brand/Brand Guidelines.md
 *
 * "Colour is a signal of state, not personality."
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
        // CELESTE BRAND COLORS
        // =======================================================================

        // Neutral Foundation (80-90% of interface)
        celeste: {
          // Whites
          'white': '#FFFFFF',
          'white-soft': '#FAFAFA',
          'white-muted': '#F8F8F0',
          'white-dim': '#F4F4F4',

          // Blacks
          'black': '#020202',
          'black-deep': '#181818',
          'black-base': '#242424',

          // Functional Blue (selection, focus only)
          'blue': '#0070FF',
          'blue-secondary': '#00A4FF',
          'blue-soft': '#BADDE9',

          // Semantic Text
          'text-primary': '#F5F5F7',
          'text-secondary': '#98989F',
          'text-muted': '#86868B',
          'text-disabled': '#636366',

          // Semantic Backgrounds
          'bg-primary': '#1C1C1E',
          'bg-secondary': '#2C2C2E',
          'bg-tertiary': '#3D3D3F',

          // Borders
          'border': '#3D3D3F',
          'border-subtle': 'rgba(61, 61, 63, 0.3)',
        },

        // Restricted Colors (specific contexts only)
        restricted: {
          'red': '#FF3B30',      // Irreversible destructive only
          'orange': '#FF9500',   // Inspection warnings only
          'yellow': '#FFCC00',   // Time-sensitive only
          'green': '#34C759',    // Committed confirmation only
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
      },

      // =========================================================================
      // BORDER RADIUS
      // =========================================================================
      borderRadius: {
        'celeste-sm': '4px',
        'celeste-md': '8px',
        'celeste-lg': '12px',
        'celeste-xl': '16px',
        'celeste-2xl': '18px',    // Spotlight panel
      },

      // =========================================================================
      // SHADOWS
      // =========================================================================
      boxShadow: {
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
