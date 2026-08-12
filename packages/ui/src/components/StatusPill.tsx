import * as React from "react";
import { Badge, type BadgeProps } from "./ui/badge.js";

export type Status =
  | "open"
  | "paid"
  | "refunded"
  | "confirmed"
  | "cancelled"
  | "checked_in"
  | "pending"
  | "completed"
  | "no_show"
  | "failed"
  | "expired"
  | "active"
  | "inactive";

interface StatusPillProps {
  status: Status;
  className?: string;
}

/**
 * Maps status strings to Badge variants and human-readable labels.
 * Semantic mapping follows common payment/booking conventions.
 */
const statusConfig: Record<Status, { variant: BadgeProps["variant"]; label: string }> = {
  // Payment statuses
  open: { variant: "warning", label: "Open" },
  paid: { variant: "success", label: "Paid" },
  refunded: { variant: "muted", label: "Refunded" },
  failed: { variant: "destructive", label: "Failed" },
  expired: { variant: "destructive", label: "Expired" },

  // Booking statuses
  confirmed: { variant: "success", label: "Confirmed" },
  cancelled: { variant: "destructive", label: "Cancelled" },
  checked_in: { variant: "default", label: "Checked in" },
  pending: { variant: "warning", label: "Pending" },
  completed: { variant: "default", label: "Completed" },
  no_show: { variant: "destructive", label: "No show" },

  // General statuses
  active: { variant: "success", label: "Active" },
  inactive: { variant: "muted", label: "Inactive" },
};

/**
 * Semantic status pill component.
 * Renders a Badge with the appropriate variant based on the status string.
 * Use for invoices, bookings, subscriptions, and user status.
 */
export function StatusPill({ status, className }: StatusPillProps) {
  const config = statusConfig[status];

  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  );
}
