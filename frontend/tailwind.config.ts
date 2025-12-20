import type { Config } from 'tailwindcss'

/**
 * CelesteOS Tailwind Configuration
 * Apple-inspired design system
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
      colors: {
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
        // Apple system colors
        system: {
          blue: 'var(--system-blue)',
          green: 'var(--system-green)',
          orange: 'var(--system-orange)',
          red: 'var(--system-red)',
          yellow: 'var(--system-yellow)',
          gray: 'var(--system-gray)',
        },
      },
      borderRadius: {
        // Apple-inspired precise radii
        lg: 'var(--radius-card)',      // 12px - cards, containers
        md: 'var(--radius-button)',    // 8px - buttons, inputs
        sm: 'var(--radius-badge)',     // 6px - badges, small elements
        xs: 'var(--radius-small)',     // 4px - tiny elements
      },
      boxShadow: {
        // Subtle, multi-layer shadows
        'xs': 'var(--shadow-xs)',
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'xl': 'var(--shadow-xl)',
      },
      fontSize: {
        // Apple typography scale
        'display': ['32px', { lineHeight: '40px', letterSpacing: '-0.02em', fontWeight: '700' }],
        'title1': ['28px', { lineHeight: '34px', letterSpacing: '-0.015em', fontWeight: '700' }],
        'title2': ['22px', { lineHeight: '28px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'title3': ['20px', { lineHeight: '24px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'headline': ['17px', { lineHeight: '22px', letterSpacing: '-0.005em', fontWeight: '600' }],
        'body': ['17px', { lineHeight: '22px', letterSpacing: '0', fontWeight: '400' }],
        'callout': ['16px', { lineHeight: '21px', letterSpacing: '0', fontWeight: '400' }],
        'subhead': ['15px', { lineHeight: '20px', letterSpacing: '0', fontWeight: '400' }],
        'footnote': ['13px', { lineHeight: '18px', letterSpacing: '0', fontWeight: '400' }],
        'caption1': ['12px', { lineHeight: '16px', letterSpacing: '0', fontWeight: '400' }],
        'caption2': ['11px', { lineHeight: '13px', letterSpacing: '0.01em', fontWeight: '400' }],
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-in': {
          '0%': { transform: 'translateY(4px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'scale-in': {
          '0%': { transform: 'scale(0.97)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
      animation: {
        'fade-in': 'fade-in 150ms ease-out',
        'slide-in': 'slide-in 200ms ease-out',
        'scale-in': 'scale-in 150ms ease-out',
      },
      transitionTimingFunction: {
        'out': 'ease-out',
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
}
export default config
