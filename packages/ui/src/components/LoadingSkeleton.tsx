import * as React from "react";
import { cn } from "../lib/cn.js";

export interface LoadingSkeletonProps {
  lines?: number;
  withCard?: boolean;
  className?: string;
  "data-testid"?: string;
}

export function LoadingSkeleton({
  lines = 3,
  withCard = false,
  className,
  ...rest
}: LoadingSkeletonProps) {
  const arr = Array.from({ length: lines });
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-testid={rest["data-testid"]}
      className={cn("w-full space-y-3", className)}
    >
      <span className="sr-only">Loading...</span>
      {withCard && (
        <div
          data-skeleton-card
          className="rounded-lg border bg-card p-6 shadow-sm"
        >
          <div className="h-4 w-1/3 animate-pulse rounded bg-muted" />
          <div className="mt-3 h-3 w-1/2 animate-pulse rounded bg-muted" />
        </div>
      )}
      {arr.map((_, i) => (
        <div
          key={i}
          data-skeleton-line
          className={cn(
            "h-3 animate-pulse rounded bg-muted",
            i === arr.length - 1 ? "w-2/3" : "w-full",
          )}
        />
      ))}
    </div>
  );
}
