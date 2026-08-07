import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the api-client BEFORE importing anything else
vi.mock("@splashh/api-client", async () => {
  const mockApi = {
    get: vi.fn(),
    post: vi.fn(),
  };
  return {
    api: mockApi,
    // Re-export other things that might be needed
    queryKeys: { bookings: {} },
    createQueryClient: vi.fn(),
    useAuthStore: { getState: vi.fn() },
    silentRefresh: vi.fn(),
  };
});

// Import AFTER the mock is defined - this gets the mocked version
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api } from "@splashh/api-client";
import { createPaymentLink, listInvoices, getInvoice, refundInvoice } from "@splashh/api-client/payments";

describe("payments api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("createPaymentLink posts to /payments/invoices/:id/payment-link with Idempotency-Key", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.post as any).mockResolvedValue({
      data: {
        short_url: "https://rzp.io/i/abc",
        razorpay_payment_link_id: "plink_abc",
        expires_at: "2026-01-01T00:00:00Z"
      }
    });
    await createPaymentLink("inv-1", "idem-1");
    expect(api.post).toHaveBeenCalledWith(
      "/payments/invoices/inv-1/payment-link",
      undefined,
      { headers: { "Idempotency-Key": "idem-1" } },
    );
  });

  it("listInvoices sends status and customer_id query params", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.get as any).mockResolvedValue({ data: [] });
    await listInvoices({ status: "paid", customer_id: "cust-1" });
    expect(api.get).toHaveBeenCalledWith("/payments/invoices", { params: { status: "paid", customer_id: "cust-1" } });
  });

  it("refundInvoice posts to /payments/invoices/:id/refund", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.post as any).mockResolvedValue({ data: { id: "r1" } });
    await refundInvoice("inv-1", "reason", "idem-2");
    expect(api.post).toHaveBeenCalledWith(
      "/payments/invoices/inv-1/refund",
      { reason: "reason" },
      { headers: { "Idempotency-Key": "idem-2" } },
    );
  });

  it("getInvoice gets a single invoice by id", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api.get as any).mockResolvedValue({ data: { id: "inv-1" } });
    await getInvoice("inv-1");
    expect(api.get).toHaveBeenCalledWith("/payments/invoices/inv-1");
  });
});
