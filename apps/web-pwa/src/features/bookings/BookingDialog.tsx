import { Button, FormField, Input } from "@splashh/ui";
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@splashh/api-client";
import { useCreateBooking } from "./useCreateBooking";

/**
 * Macha/neon booking dialog. Uses native <dialog> for free focus trap,
 * Escape-to-close, and screen-reader semantics.
 */
export function BookingDialog({
  resourceId,
  resourceName,
  facilityName,
  onClose,
}: {
  resourceId: string;
  resourceName?: string;
  facilityName?: string;
  onClose: () => void;
}) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const create = useCreateBooking();
  const customerId = useAuthStore((s) => s.customerId);
  const ref = useRef<HTMLDialogElement>(null);

  // Open / close the native dialog on mount / unmount.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!el.open) el.showModal();
    return () => {
      if (el.open) el.close();
    };
  }, []);

  // Native <dialog> closes itself on Escape — surface that to the parent.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handler = () => onClose();
    el.addEventListener("close", handler);
    return () => el.removeEventListener("close", handler);
  }, [onClose]);

  const handleStartChange = (value: string) => {
    setStart(value);
    if (value) {
      const startDate = new Date(value);
      startDate.setMinutes(startDate.getMinutes() + 60);
      setEnd(startDate.toISOString().slice(0, 16));
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerId || !start || !end) return;
    try {
      // Note: price_cents is NOT sent - server computes from BookingTariff (F-05 fix)
      await create.mutateAsync({
        customer_id: customerId,
        resource_id: resourceId,
        start_at: new Date(start).toISOString(),
        end_at: new Date(end).toISOString(),
      });
      onClose();
    } catch {
      /* error surfaced via mutation state */
    }
  };

  return (
    <dialog
      ref={ref}
      aria-labelledby="book-dialog-title"
      className="m-auto max-w-md border-2 border-border bg-card p-0 shadow-volt-lg text-foreground backdrop:bg-black/60 animate-score-pop motion-reduce:animate-none"
    >
      <form onSubmit={onSubmit} className="space-y-4 p-6">
        <header className="flex items-start justify-between gap-3 border-b-2 border-border pb-4">
          <div>
            <p className="font-display text-[10px] uppercase tracking-[0.18em] text-volt">
              {facilityName ?? "Facility"}
            </p>
            <h2 id="book-dialog-title" className="font-display text-2xl font-bold uppercase tracking-tight">
              Book {resourceName ?? "resource"}
            </h2>
          </div>
          <button
            type="button"
            aria-label="Close booking dialog"
            onClick={onClose}
            className="inline-flex h-8 w-8 items-center justify-center border-2 border-border text-muted-foreground hover:border-primary hover:text-primary transition-colors duration-200"
          >
            <span aria-hidden>×</span>
          </button>
        </header>

        <FormField label="Start" htmlFor="book-start">
          <Input
            id="book-start"
            type="datetime-local"
            value={start}
            onChange={(e) => handleStartChange(e.target.value)}
            required
          />
        </FormField>
        <FormField label="End (auto, 60 min)" htmlFor="book-end">
          <Input
            id="book-end"
            type="datetime-local"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            required
          />
        </FormField>

        {create.error && (
          <p role="alert" aria-live="assertive" className="border-2 border-destructive bg-destructive/10 p-3 text-sm text-destructive">
            Something went wrong. Please try again, or contact your club if the problem continues.
          </p>
        )}

        <footer className="flex justify-end gap-2 border-t-2 border-border pt-4">
          <Button variant="ghost" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={create.isPending || !customerId || !start || !end}>
            {create.isPending ? "Booking…" : "Confirm booking"}
          </Button>
        </footer>
      </form>
    </dialog>
  );
}
