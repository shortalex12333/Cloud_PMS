import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

/**
 * Button variants - Apple-inspired design
 *
 * Key changes from generic SaaS:
 * - 8px border radius (not rounded-full)
 * - Subtle shadows on primary
 * - 15px font size (Apple standard)
 * - Precise padding following 8px grid
 * - Smooth 150ms transitions
 */
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap text-[15px] font-medium ring-offset-background transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[--system-blue] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default:
          'bg-[--system-blue] text-white shadow-[0_1px_2px_rgba(0,0,0,0.08)] hover:bg-[#0066CC] hover:shadow-[0_2px_4px_rgba(0,0,0,0.1)]',
        destructive:
          'bg-[--system-red] text-white shadow-[0_1px_2px_rgba(0,0,0,0.08)] hover:bg-[#E6352B]',
        outline:
          'border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-900 dark:text-zinc-100',
        secondary:
          'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-200 dark:hover:bg-zinc-700',
        ghost:
          'hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-200',
        link:
          'text-[--system-blue] underline-offset-4 hover:underline',
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
