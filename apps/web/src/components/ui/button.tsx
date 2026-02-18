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
  'inline-flex items-center justify-center gap-2 whitespace-nowrap text-[15px] font-medium ring-offset-background transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        // Default: Transparent with border (per brand spec)
        default:
          'bg-transparent border border-surface-border text-txt-secondary hover:text-txt-primary hover:bg-brand-interactive-soft dark:border-surface-border dark:text-txt-secondary dark:hover:text-txt-primary',
        // Accent: Maritime teal - primary CTA
        accent:
          'bg-brand-interactive text-white shadow-[0_1px_2px_rgba(0,0,0,0.08)] hover:bg-brand-interactive-hover hover:shadow-[0_2px_4px_rgba(0,0,0,0.12)]',
        // Destructive: Muted red - irreversible actions only
        destructive:
          'bg-status-critical text-white shadow-[0_1px_2px_rgba(0,0,0,0.08)] hover:bg-status-critical/90',
        // Outline: Border emphasis
        outline:
          'border border-surface-border dark:border-surface-border bg-surface-primary dark:bg-surface-primary hover:bg-surface-hover dark:hover:bg-surface-hover text-txt-primary dark:text-txt-primary',
        // Secondary: Subtle background
        secondary:
          'bg-surface-hover dark:bg-surface-hover text-txt-primary dark:text-txt-primary hover:bg-surface-elevated dark:hover:bg-surface-elevated',
        // Ghost: No background until hover
        ghost:
          'hover:bg-brand-interactive-soft text-txt-secondary hover:text-txt-primary dark:text-txt-secondary dark:hover:text-txt-primary',
        // Link: Text only with underline
        link:
          'text-brand-interactive underline-offset-4 hover:underline',
        // Warning: For cautionary actions
        warning:
          'bg-transparent border border-status-critical text-status-critical hover:bg-status-critical/10',
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
