import { type VariantProps, cva } from "class-variance-authority";
import type * as React from "react";
import { cn } from "../../lib/cn.js";

// Macha/neon badge: sharp corners, hard 2px border, uppercase tracking.
const badgeVariants = cva(
  "inline-flex items-center px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        // Brand volt
        default: "bg-primary text-primary-foreground border-2 border-black",
        // Warm orange accent
        accent: "bg-accent-warm text-black border-2 border-black",
        // Success green
        success: "bg-success text-success-foreground border-2 border-black",
        // Warning amber
        warning: "bg-warning text-warning-foreground border-2 border-black",
        // Destructive red
        destructive: "bg-destructive text-destructive-foreground border-2 border-black",
        // Muted — outlined, no fill
        muted: "bg-transparent text-muted-foreground border-2 border-border",
        // Outline — volt border on transparent bg
        outline: "bg-transparent text-primary border-2 border-primary",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
