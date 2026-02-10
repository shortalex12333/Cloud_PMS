import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

/**
 * Button variants - CelesteOS Maritime Design
 * Source: BRANDING_V3
 *
 * Key principles:
 * - 8px border radius (not rounded-full)
 * - Maritime teal accent (#3A7C9D)
 * - Muted restricted colors for destructive
 * - Transparent default buttons per brand spec
 * - Smooth 150ms transitions
 */
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap text-[15px] font-medium ring-offset-background transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        // Default: Transparent with border (per brand spec)
        default:
          'bg-transparent border border-celeste-border text-celeste-text-secondary hover:text-celeste-text-primary hover:bg-celeste-accent-soft dark:border-celeste-border dark:text-celeste-text-secondary dark:hover:text-celeste-text-primary',
        // Accent: Maritime teal - primary CTA
        accent:
          'bg-celeste-accent text-celeste-white shadow-[0_1px_2px_rgba(0,0,0,0.08)] hover:bg-celeste-accent-hover hover:shadow-[0_2px_4px_rgba(0,0,0,0.12)]',
        // Destructive: Muted red - irreversible actions only
        destructive:
          'bg-restricted-red text-celeste-white shadow-[0_1px_2px_rgba(0,0,0,0.08)] hover:bg-restricted-red/90',
        // Outline: Border emphasis
        outline:
          'border border-celeste-border-light dark:border-celeste-border bg-celeste-white dark:bg-celeste-bg-primary hover:bg-celeste-bg-secondary-light dark:hover:bg-celeste-bg-secondary text-celeste-text-primary-light dark:text-celeste-text-primary',
        // Secondary: Subtle background
        secondary:
          'bg-celeste-bg-secondary-light dark:bg-celeste-bg-secondary text-celeste-text-primary-light dark:text-celeste-text-primary hover:bg-celeste-bg-tertiary-light dark:hover:bg-celeste-bg-tertiary',
        // Ghost: No background until hover
        ghost:
          'hover:bg-celeste-accent-soft text-celeste-text-secondary hover:text-celeste-text-primary dark:text-celeste-text-secondary dark:hover:text-celeste-text-primary',
        // Link: Text only with underline
        link:
          'text-celeste-accent underline-offset-4 hover:underline',
        // Warning: For cautionary actions
        warning:
          'bg-transparent border border-restricted-red text-restricted-red hover:bg-restricted-red/10',
      },
      size: {
        default: 'h-10 px-4 py-2 rounded-[8px]',
        sm: 'h-8 px-3 text-[13px] rounded-[6px]',
        lg: 'h-12 px-6 text-[17px] rounded-[10px]',
        icon: 'h-10 w-10 rounded-[8px]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
