import * as React from "react";
import { cn } from "../lib/cn.js";

export interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
  "data-testid"?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
  className,
  ...rest
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      data-testid={rest["data-testid"]}
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-4 py-12 text-center",
        className,
      )}
    >
      <h2 className="text-lg font-semibold">{title}</h2>
      {description && (
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          Retry
        </button>
      )}
    </div>
  );
}
