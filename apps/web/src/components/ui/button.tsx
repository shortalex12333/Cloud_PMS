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
  '',
  {
    variants: {
      variant: {
        // Default: Ghost button style
        default: 'btn-ghost',
        // Accent: Primary button - maritime teal
        accent: 'btn-primary',
        // Destructive: Danger button - muted red
        destructive: 'btn-danger',
        // Outline: Ghost button style
        outline: 'btn-ghost',
        // Secondary: Ghost button style
        secondary: 'btn-ghost',
        // Ghost: Ghost button style
        ghost: 'btn-ghost',
        // Link: Text only with underline
        link: 'text-celeste-accent underline-offset-4 hover:underline',
        // Warning: Danger button style
        warning: 'btn-danger',
      },
      size: {
        default: '',
        sm: '',
        lg: '',
        icon: 'btn-icon',
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
