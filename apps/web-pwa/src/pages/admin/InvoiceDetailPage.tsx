import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "@splashh/ui";
import { useInvoice, useRefundInvoice } from "@/features/payments/hooks";
import { useAuthStore } from "@splashh/api-client";

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: inv, isLoading } = useInvoice(id);
  const roles = useAuthStore((s) => s.roles);
  const refund = useRefundInvoice();
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);

  if (isLoading) return <div className="container py-6">Loading...</div>;
  if (!inv) return <div className="container py-6 text-destructive">Invoice not found.</div>;

  return (
    <div className="container py-6">
      <h1 className="text-2xl font-semibold">{inv.invoice_number}</h1>
      <p data-testid="invoice-status" className="text-sm text-muted-foreground">
        Status: {inv.status}
      </p>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Line items</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-1 text-sm">
            {inv.line_items.map((li) => (
              <li key={li.id} className="flex justify-between">
                <span>
                  {li.description} x {li.quantity}
                </span>
                <span>INR {(li.total_paise / 100).toFixed(2)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 font-semibold">
            Total: INR {(inv.total_paise / 100).toFixed(2)}
          </p>
        </CardContent>
      </Card>

      {roles.includes("tenant_admin") && inv.status === "paid" && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-base">Refund</CardTitle>
          </CardHeader>
          <CardContent>
            {!confirming && (
              <Button onClick={() => setConfirming(true)} variant="destructive">
                Refund
              </Button>
            )}
            {confirming && (
              <div className="space-y-2">
                <Input
                  placeholder="Reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button
                    onClick={() =>
                      refund.mutate({
                        invoiceId: inv.id,
                        reason,
                        idempotencyKey: crypto.randomUUID(),
                      })
                    }
                    disabled={!reason || refund.isPending}
                  >
                    Confirm refund
                  </Button>
                  <Button variant="ghost" onClick={() => setConfirming(false)}>
                    Cancel
                  </Button>
                </div>
                {refund.error && (
                  <p className="text-sm text-destructive">
                    {(refund.error as Error).message}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
