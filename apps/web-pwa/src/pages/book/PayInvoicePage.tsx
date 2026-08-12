import { useCreatePaymentLink, useInvoice } from "@/features/payments/hooks";
import type { InvoiceStatus } from "@splashh/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, StatusPill } from "@splashh/ui";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";

function formatCurrency(amountPaise: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
  }).format(amountPaise / 100);
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

function isPastDue(dueDate: string): boolean {
  return new Date(dueDate) < new Date();
}

export function PayInvoicePage() {
  const { id } = useParams<{ id: string }>();
  const { data: inv, isLoading, error } = useInvoice(id);
  const paymentLink = useCreatePaymentLink();

  if (isLoading) return <div className="container py-6">Loading...</div>;
  if (error || !inv)
    return <div className="container py-6 text-destructive">Invoice not found.</div>;

  const onPay = () => {
    paymentLink.mutate(
      { invoiceId: inv.id, idempotencyKey: crypto.randomUUID() },
      {
        onSuccess: (res) => {
          window.location.href = res.short_url;
        },
      },
    );
  };

  const isPaid = inv.status === "paid";
  const pastDue = !isPaid && isPastDue(inv.due_date);

  return (
    <div className="container max-w-md py-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Pay invoice {inv.invoice_number}</h1>
        <StatusPill status={mapStatusToPill(inv.status)} />
      </div>

      {pastDue && (
        <div className="mb-4 p-3 rounded-none bg-amber-50 border border-amber-200 dark:bg-amber-950/30 dark:border-amber-800 flex items-start gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
              Payment overdue
            </p>
            <p className="text-sm text-amber-700 dark:text-amber-300">
              This invoice was due on {inv.due_date}.
            </p>
          </div>
        </div>
      )}

      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">{inv.description || "Amount due"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Line items table */}
          {inv.line_items && inv.line_items.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2">Line items</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-1 font-medium">Description</th>
                    <th className="pb-1 font-medium text-right">Qty</th>
                    <th className="pb-1 font-medium text-right">Unit Price</th>
                    <th className="pb-1 font-medium text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {inv.line_items.map((item) => (
                    <tr key={item.id} className="border-b last:border-0">
                      <td className="py-2">{item.description}</td>
                      <td className="py-2 text-right">{item.quantity}</td>
                      <td className="py-2 text-right">
                        {formatCurrency(item.unit_price_paise, inv.currency)}
                      </td>
                      <td className="py-2 text-right">
                        {formatCurrency(item.total_paise, inv.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Subtotal / Tax / Total breakdown */}
          {inv.tax_paise > 0 && (
            <div className="space-y-1 pt-2 border-t">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Subtotal</span>
                <span>{formatCurrency(inv.subtotal_paise, inv.currency)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Tax</span>
                <span>{formatCurrency(inv.tax_paise, inv.currency)}</span>
              </div>
              <div className="flex justify-between font-semibold text-lg pt-2 border-t">
                <span>Total</span>
                <span>{formatCurrency(inv.total_paise, inv.currency)}</span>
              </div>
            </div>
          )}

          {(!inv.line_items || inv.line_items.length === 0) && (
            <p className="text-3xl font-semibold">
              {formatCurrency(inv.total_paise, inv.currency)}
            </p>
          )}

          <p className="text-sm text-muted-foreground">Due {inv.due_date}</p>
        </CardContent>
      </Card>

      {isPaid ? (
        <div className="mt-4">
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400 mb-3">
            <CheckCircle2 className="h-5 w-5" />
            <span className="font-medium">This invoice is paid</span>
          </div>
          <Button asChild variant="outline" className="w-full">
            <Link to="/book/bookings">View my bookings</Link>
          </Button>
        </div>
      ) : (
        <>
          <Button onClick={onPay} disabled={paymentLink.isPending} className="mt-4 w-full">
            {paymentLink.isPending ? "Loading payment..." : "Pay with card"}
          </Button>
          {paymentLink.error && (
            <p className="mt-2 text-sm text-destructive">{(paymentLink.error as Error).message}</p>
          )}
        </>
      )}
    </div>
  );
}
