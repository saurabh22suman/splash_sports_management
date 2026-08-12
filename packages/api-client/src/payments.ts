import { api } from "@splashh/api-client";

export type InvoiceStatus = "draft" | "pending" | "paid" | "failed" | "cancelled" | "refunded";

export interface LineItem {
  id: string;
  description: string;
  quantity: number;
  unit_price_paise: number;
  total_paise: number;
}

export interface Invoice {
  id: string;
  tenant_id: string;
  customer_id: string;
  invoice_number: string;
  status: InvoiceStatus;
  subtotal_paise: number;
  tax_paise: number;
  total_paise: number;
  currency: string;
  due_date: string;
  paid_at: string | null;
  description: string;
  line_items: LineItem[];
  created_at: string;
  updated_at: string;
}

export interface PaymentLinkResponse {
  short_url: string;
  razorpay_payment_link_id: string;
  expires_at: string | null;
}

export interface Refund {
  id: string;
  payment_id: string;
  amount_paise: number;
  currency: string;
  status: "pending" | "completed" | "failed";
  reason: string;
  razorpay_refund_id: string | null;
  created_at: string;
}

export interface ListInvoicesParams {
  status?: InvoiceStatus;
  customer_id?: string;
  limit?: number;
  offset?: number;
}

export async function listInvoices(params?: ListInvoicesParams): Promise<Invoice[]> {
  const { data } = await api.get<Invoice[]>("/payments/invoices", { params });
  return data;
}

export async function getInvoice(id: string): Promise<Invoice> {
  const { data } = await api.get<Invoice>(`/payments/invoices/${id}`);
  return data;
}

export interface CreateInvoiceInput {
  customer_id: string;
  line_items: Omit<LineItem, "id" | "total_paise">[];
  description: string;
  due_date: string;
}

export async function createInvoice(
  input: CreateInvoiceInput,
  idempotencyKey?: string,
): Promise<Invoice> {
  const { data } = await api.post<Invoice>(
    "/payments/invoices",
    input,
    idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined,
  );
  return data;
}

export async function createPaymentLink(
  invoiceId: string,
  idempotencyKey: string,
): Promise<PaymentLinkResponse> {
  const { data } = await api.post<PaymentLinkResponse>(
    `/payments/invoices/${invoiceId}/payment-link`,
    undefined,
    { headers: { "Idempotency-Key": idempotencyKey } },
  );
  return data;
}

export async function refundInvoice(
  invoiceId: string,
  reason: string,
  idempotencyKey: string,
): Promise<Refund> {
  const { data } = await api.post<Refund>(
    `/payments/invoices/${invoiceId}/refund`,
    { reason },
    { headers: { "Idempotency-Key": idempotencyKey } },
  );
  return data;
}
