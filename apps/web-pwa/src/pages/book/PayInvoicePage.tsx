import { useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";
import { useInvoice, useCreatePaymentLink } from "@/features/payments/hooks";

export function PayInvoicePage() {
  const { id } = useParams<{ id: string }>();
  const { data: inv, isLoading, error } = useInvoice(id);
  const paymentLink = useCreatePaymentLink();

  if (isLoading) return <div className="container py-6">Loading...</div>;
  if (error || !inv) return <div className="container py-6 text-destructive">Invoice not found.</div>;

  const onPay = () => {
    paymentLink.mutate(
      { invoiceId: inv.id, idempotencyKey: crypto.randomUUID() },
      { onSuccess: (res) => { window.location.href = res.short_url; } },
    );
  };

  return (
    <div className="container max-w-md py-6">
      <h1 className="text-2xl font-semibold">Pay invoice {inv.invoice_number}</h1>
      <Card className="mt-4">
        <CardHeader><CardTitle className="text-base">{inv.description || "Amount due"}</CardTitle></CardHeader>
        <CardContent>
          <p className="text-3xl font-semibold">INR {(inv.total_paise / 100).toFixed(2)}</p>
          <p className="text-sm text-muted-foreground">Due {inv.due_date}</p>
        </CardContent>
      </Card>
      <Button onClick={onPay} disabled={paymentLink.isPending} className="mt-4 w-full">
        {paymentLink.isPending ? "Loading payment..." : "Pay with card"}
      </Button>
      {paymentLink.error && <p className="mt-2 text-sm text-destructive">{(paymentLink.error as Error).message}</p>}
    </div>
  );
}
