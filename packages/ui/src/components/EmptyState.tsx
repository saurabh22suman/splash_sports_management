import type * as React from "react";
import { Link } from "react-router-dom";
import { cn } from "../lib/cn.js";
import { Button } from "./ui/button.js";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void } | { label: string; to: string };
  className?: string;
  "data-testid"?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  ...rest
}: EmptyStateProps) {
  return (
    <div
      data-testid={rest["data-testid"]}
      className={cn(
        "flex flex-col items-center justify-center gap-4 border-2 border-dashed border-border bg-card/30 px-4 py-16 text-center",
        className,
      )}
    >
      {icon && <div className="text-muted-foreground">{icon}</div>}
      <h2 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">
        {title}
      </h2>
      {description && <p className="max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && "to" in action ? (
        <Button asChild>
          <Link to={action.to}>{action.label}</Link>
        </Button>
      ) : (
        action && <Button onClick={action.onClick}>{action.label}</Button>
      )}
    </div>
  );
}
