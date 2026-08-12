import { Button } from "@splashh/ui";
import { useRef } from "react";

/**
 * Native <dialog>-based confirmation. Open via the `open` prop; the parent
 * gets `onClose` back when the user dismisses (cancel button, backdrop click,
 * or Escape).
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  isPending = false,
  onClose,
  onConfirm,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  isPending?: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  // Sync the `open` prop with the native dialog state.
  if (open && ref.current && !ref.current.open) ref.current.showModal();
  if (!open && ref.current?.open) ref.current.close();

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => {
        // Backdrop click closes (clicks on the dialog itself don't propagate
        // out of the inner content because of the inner padding wrapper).
        if (e.target === ref.current) onClose();
      }}
      aria-labelledby="confirm-title"
      className={`m-auto max-w-md border-2 p-0 shadow-volt-lg text-foreground backdrop:bg-black/60 ${
        destructive ? "border-destructive bg-card" : "border-border bg-card"
      }`}
    >
      <div className="p-6">
        <h2 id="confirm-title" className="font-display text-2xl font-bold uppercase tracking-tight">
          {title}
        </h2>
        <p className="mt-3 text-sm text-muted-foreground">{description}</p>
        <div className="mt-6 flex justify-end gap-2 border-t-2 border-border pt-4">
          <Button variant="ghost" type="button" onClick={onClose} disabled={isPending}>
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            type="button"
            onClick={onConfirm}
            disabled={isPending}
          >
            {isPending ? "Working…" : confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  );
}
