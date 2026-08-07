import { Button, Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";
import { Link } from "react-router-dom";
import { useInvoices } from "@/features/payments/hooks";
import { useState } from "react";
import type { InvoiceStatus } from "@splashh/api-client";

export function InvoicesPage() {
  const [status, setStatus] = useState<InvoiceStatus | undefined>(undefined);
  const { data, isLoading, error } = useInvoices({ status });

  return (
    <div className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Invoices</h1>
        <Button asChild>
          <Link to="/admin/invoices/new">+ New invoice</Link>
        </Button>
      </div>
      <div className="mb-3 flex gap-2 text-sm">
        {(["all", "pending", "paid", "refunded"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s === "all" ? undefined : s)}
            className={`px-3 py-1 rounded border ${(status ?? "all") === s ? "bg-sky-50 border-sky-500" : ""}`}
          >
            {s}
          </button>
        ))}
      </div>
      {isLoading && <p>Loading...</p>}
      {error && <p className="text-destructive">Failed to load invoices.</p>}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">All invoices</CardTitle>
        </CardHeader>
        <CardContent>
          {data?.length === 0 && <p className="text-sm text-muted-foreground">No invoices yet.</p>}
          <table className="w-full">
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
              {data?.map((inv) => (
                <tr key={inv.id} className="border-b last:border-0">
                  <td className="py-3">
                    <Link to={`/admin/invoices/${inv.id}`} className="hover:underline">
                      {inv.invoice_number}
                    </Link>
                  </td>
                  <td className="py-3">{inv.customer_id.slice(0, 8)}</td>
                  <td className="py-3">INR {(inv.total_paise / 100).toFixed(2)}</td>
                  <td className="py-3">{inv.status}</td>
                  <td className="py-3">{inv.due_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
