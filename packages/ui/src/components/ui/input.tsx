import * as React from "react";
import { cn } from "../../lib/cn.js";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

// Sharp input — 2px border that goes volt on focus with a soft neon glow.
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-11 w-full border-2 border-border bg-input px-4 py-2 text-sm text-foreground placeholder:text-muted-foreground transition-all duration-200 ease-out",
        "focus-visible:outline-none focus-visible:border-primary focus-visible:shadow-volt-sm",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
