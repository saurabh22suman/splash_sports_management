import {
  type InvoiceStatus,
  createInvoice,
  createPaymentLink,
  getInvoice,
  listInvoices,
  refundInvoice,
} from "@splashh/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export const paymentKeys = {
  all: ["payments"] as const,
  list: (params?: object) => [...paymentKeys.all, "list", params] as const,
  detail: (id: string) => [...paymentKeys.all, "detail", id] as const,
};

export function useInvoices(params?: { status?: InvoiceStatus; customer_id?: string }) {
  return useQuery({
    queryKey: paymentKeys.list(params),
    queryFn: () => listInvoices(params),
  });
}

export function useInvoice(id: string | undefined) {
  return useQuery({
    queryKey: paymentKeys.detail(id!),
    queryFn: () => getInvoice(id!),
    enabled: !!id,
  });
}

export function useCreatePaymentLink() {
  return useMutation({
    mutationFn: ({ invoiceId, idempotencyKey }: { invoiceId: string; idempotencyKey: string }) =>
      createPaymentLink(invoiceId, idempotencyKey),
  });
}

export function useRefundInvoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      invoiceId,
      reason,
      idempotencyKey,
    }: { invoiceId: string; reason: string; idempotencyKey: string }) =>
      refundInvoice(invoiceId, reason, idempotencyKey),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: paymentKeys.detail(vars.invoiceId) });
      qc.invalidateQueries({ queryKey: paymentKeys.all });
    },
  });
}
