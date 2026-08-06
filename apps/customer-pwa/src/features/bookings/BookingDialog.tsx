import { Button, FormField, Input } from "@splashh/ui";
import { useState } from "react";
import { useAuthStore } from "@splashh/api-client";
import { useCreateBooking } from "./useCreateBooking";

export function BookingDialog({
  resourceId,
  onClose,
}: {
  resourceId: string;
  onClose: () => void;
}) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [price, setPrice] = useState(2500);
  const create = useCreateBooking();
  const customerId = useAuthStore((s) => s.userId);

  const onSubmit = async () => {
    if (!customerId || !start || !end) return;
    try {
      await create.mutateAsync({
        customer_id: customerId,
        resource_id: resourceId,
        start_at: new Date(start).toISOString(),
        end_at: new Date(end).toISOString(),
        price_cents: price,
        currency: "AUD",
      });
      onClose();
    } catch {
      /* error surfaced via mutation state */
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    >
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg">
        <h2 className="text-lg font-semibold">Book resource</h2>
        <div className="mt-4 space-y-3">
          <FormField label="Start">
            <Input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
          </FormField>
          <FormField label="End">
            <Input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
          </FormField>
          <FormField label="Price (cents)">
            <Input type="number" min={0} value={price} onChange={(e) => setPrice(Number(e.target.value))} />
          </FormField>
          {create.error && (
            <p role="alert" className="text-sm text-destructive">
              {(create.error as Error).message}
            </p>
          )}
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={create.isPending}>
            {create.isPending ? "Booking…" : "Confirm booking"}
          </Button>
        </div>
      </div>
    </div>
  );
}
