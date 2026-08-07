import { useParams, Link } from "react-router-dom";
import { Button, Card, CardContent } from "@splashh/ui";
import { useInvoice } from "@/features/payments/hooks";

export function PayInvoiceReturnPage() {
  const { id } = useParams<{ id: string }>();
  const { data: inv, isLoading, refetch } = useInvoice(id);

  if (isLoading) return <div className="container py-6">Loading...</div>;

  return (
    <div className="container max-w-md py-6">
      <Card>
        <CardContent className="py-6 text-center">
          {inv?.status === "paid" ? (
            <>
              <p className="text-lg font-semibold">Payment successful</p>
              <p className="text-sm text-muted-foreground">Invoice {inv.invoice_number}</p>
              <Button asChild className="mt-4"><Link to="/book/bookings">My bookings</Link></Button>
            </>
          ) : (
            <>
              <p className="text-lg font-semibold">Processing</p>
              <p className="text-sm text-muted-foreground">Your payment is being processed.</p>
              <Button onClick={() => refetch()} className="mt-4">Refresh</Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
