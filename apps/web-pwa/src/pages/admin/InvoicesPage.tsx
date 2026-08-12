import { useInvoices } from "@/features/payments/hooks";
import type { InvoiceStatus } from "@splashh/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, StatusPill } from "@splashh/ui";
import { useState } from "react";
import { Link } from "react-router-dom";

function formatCurrency(amountPaise: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
  }).format(amountPaise / 100);
}

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(dateString));
}

// Map API invoice status to StatusPill status
function mapStatusToPill(
  status: InvoiceStatus,
): "open" | "paid" | "refunded" | "failed" | "cancelled" | "pending" {
  switch (status) {
    case "draft":
      return "open";
    case "pending":
      return "pending";
    case "paid":
      return "paid";
    case "refunded":
      return "refunded";
    case "failed":
      return "failed";
    case "cancelled":
      return "cancelled";
    default:
      return "pending";
  }
}

export function InvoicesPage() {
  const [status, setStatus] = useState<InvoiceStatus | undefined>(undefined);
  const { data, isLoading, error, refetch } = useInvoices({ status });

  return (
    <div className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Invoices</h1>
        <Button asChild variant="outline">
          <Link to="/admin/invoices/new">+ New invoice</Link>
        </Button>
      </div>
      <div className="mb-3 flex gap-2">
        {(["all", "pending", "paid", "refunded"] as const).map((s) => (
          <Button
            key={s}
            variant={(status ?? "all") === s ? "default" : "outline"}
            size="sm"
            onClick={() => setStatus(s === "all" ? undefined : s)}
          >
            {s}
          </Button>
        ))}
      </div>
      {isLoading && <p>Loading...</p>}
      {error && (
        <div className="rounded-none border border-destructive p-4 text-center">
          <p className="text-destructive mb-3">Failed to load invoices.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Try again
          </Button>
        </div>
      )}
      <Card>
        <CardHeader className="sr-only">
          <CardTitle>Invoices list</CardTitle>
        </CardHeader>
        <CardContent>
          {data?.length === 0 && !isLoading && !error && (
            <div className="text-center py-6">
              <p className="text-sm text-muted-foreground mb-3">No invoices yet.</p>
              <Button asChild variant="outline" size="sm">
                <Link to="/admin/invoices/new">+ New invoice</Link>
              </Button>
            </div>
          )}
          {data && data.length > 0 && (
            <>
              {/* Mobile: card list */}
              <ul className="space-y-3 md:hidden">
                {data.map((inv, idx) => (
                  <li
                    key={inv.id}
                    className="border-2 border-border bg-card p-4 animate-rise-up motion-reduce:animate-none"
                    style={{ animationDelay: `${Math.min(idx * 60, 480)}ms` }}
                  >
                    <Link
                      to={`/admin/invoices/${inv.id}`}
                      className="flex items-center justify-between gap-3 mb-2"
                    >
                      <span className="font-display font-bold text-foreground uppercase tracking-tight">
                        {inv.invoice_number}
                      </span>
                      <StatusPill status={mapStatusToPill(inv.status)} />
                    </Link>
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">
                        {formatCurrency(inv.total_paise, inv.currency)}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {formatDate(inv.due_date)}
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-[10px] text-muted-foreground">
                      Customer {inv.customer_id.slice(0, 8)}
                    </div>
                  </li>
                ))}
              </ul>

              {/* Desktop: table */}
              <table className="w-full hidden md:table">
                <thead>
                  <tr className="border-b text-left text-sm text-muted-foreground">
                    <th className="pb-2 font-medium">Invoice #</th>
                    <th className="pb-2 font-medium">Customer</th>
                    <th className="pb-2 font-medium">Total</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Due</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((inv, idx) => (
                    <tr
                      key={inv.id}
                      className="border-b last:border-0 animate-rise-up motion-reduce:animate-none transition-colors duration-250 ease-swim hover:bg-secondary/40"
                      style={{ animationDelay: `${Math.min(idx * 60, 480)}ms` }}
                    >
                      <td className="py-3">
                        <Link
                          to={`/admin/invoices/${inv.id}`}
                          className="font-medium text-foreground hover:text-primary transition-colors duration-250"
                        >
                          {inv.invoice_number}
                        </Link>
                      </td>
                      <td className="py-3 text-sm text-muted-foreground">
                        {inv.customer_id.slice(0, 8)}
                      </td>
                      <td className="py-3 text-sm font-medium">
                        {formatCurrency(inv.total_paise, inv.currency)}
                      </td>
                      <td className="py-3">
                        <StatusPill status={mapStatusToPill(inv.status)} />
                      </td>
                      <td className="py-3 text-sm text-muted-foreground">
                        {formatDate(inv.due_date)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
