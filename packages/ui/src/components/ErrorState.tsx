import * as React from "react";
import { cn } from "../lib/cn.js";
import { Button } from "./ui/button.js";

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
        "flex flex-col items-center justify-center gap-4 border-2 border-destructive bg-destructive/10 px-4 py-12 text-center",
        className,
      )}
    >
      <h2 className="font-display text-2xl font-bold uppercase tracking-tight text-destructive">{title}</h2>
      {description && (
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
