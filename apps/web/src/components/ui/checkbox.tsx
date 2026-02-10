"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  onCheckedChange?: (checked: boolean) => void
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, onCheckedChange, checked, ...props }, ref) => {
    const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      onCheckedChange?.(event.target.checked)
    }

    return (
      <div className="relative inline-flex items-center">
        <input
          type="checkbox"
          className="sr-only peer"
          ref={ref}
          checked={checked}
          onChange={handleChange}
          {...props}
        />
        <div
          className={cn(
            "h-4 w-4 shrink-0 rounded-[4px] border border-celeste-border ring-offset-background",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent focus-visible:ring-offset-2",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "peer-checked:bg-celeste-accent peer-checked:border-celeste-accent peer-checked:text-celeste-white",
            "flex items-center justify-center cursor-pointer",
            className
          )}
          onClick={() => {
            const input = ref as React.RefObject<HTMLInputElement>
            if (input?.current) {
              input.current.click()
            }
          }}
        >
          {checked && <Check className="h-3 w-3 text-current" />}
        </div>
      </div>
    )
  }
)
Checkbox.displayName = "Checkbox"

export { Checkbox }
