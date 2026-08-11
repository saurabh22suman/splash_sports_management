import { useParams, Link } from "react-router-dom";
import { Button, Card, CardContent, StatusPill } from "@splashh/ui";
import { CheckCircle2, Clock } from "lucide-react";
import { useInvoice } from "@/features/payments/hooks";
import type { InvoiceStatus } from "@splashh/api-client";

// Map API invoice status to StatusPill status
function mapStatusToPill(status: InvoiceStatus): "open" | "paid" | "refunded" | "failed" | "cancelled" | "pending" {
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

export function PayInvoiceReturnPage() {
  const { id } = useParams<{ id: string }>();
  const { data: inv, isLoading, refetch } = useInvoice(id);

  if (isLoading) return <div className="container py-6">Loading...</div>;

  const isPaid = inv?.status === "paid";

  return (
    <div className="container max-w-md py-6">
      <Card>
        <CardContent className="py-6 text-center">
          {isPaid ? (
            <>
              <div className="flex justify-center mb-3">
                <CheckCircle2 className="h-12 w-12 text-green-500" />
              </div>
              <p className="text-lg font-semibold">Payment received</p>
              <p className="text-sm text-muted-foreground mb-2">Invoice {inv?.invoice_number}</p>
              <StatusPill status="paid" className="mb-4" />
              <Button asChild className="mt-2"><Link to="/book/bookings">My bookings</Link></Button>
            </>
          ) : (
            <>
              <div className="flex justify-center mb-3">
                <Clock className="h-12 w-12 text-amber-500" />
              </div>
              <p className="text-lg font-semibold">Processing payment</p>
              <p className="text-sm text-muted-foreground mb-2">Your payment is being processed.</p>
              {inv && <StatusPill status={mapStatusToPill(inv.status)} className="mb-4" />}
              <Button onClick={() => refetch()} className="mt-2">Refresh</Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
