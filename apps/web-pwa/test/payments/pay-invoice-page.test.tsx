import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/features/payments/hooks", () => ({
  useInvoice: () => ({
    data: {
      id: "i1",
      invoice_number: "INV-000001",
      status: "pending",
      total_paise: 150000,
      currency: "INR",
      description: "Booking #abc",
      due_date: "2026-09-01",
      line_items: [],
      subtotal_paise: 150000,
      tax_paise: 0,
      paid_at: null,
      created_at: "",
      updated_at: "",
      customer_id: "c1",
      tenant_id: "t1",
    },
    isLoading: false,
  }),
  useCreatePaymentLink: () => ({
    mutate: vi.fn((args: any, opts: any) =>
      opts.onSuccess({
        short_url: "https://rzp.io/i/test",
        razorpay_payment_link_id: "plink_test",
        expires_at: "",
      })
    ),
    isPending: false,
  }),
}));

import { PayInvoicePage } from "@/pages/book/PayInvoicePage";

describe("PayInvoicePage", () => {
  let originalLocation: Location;

  beforeEach(() => {
    originalLocation = window.location;
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
      configurable: true,
    });
  });

  it("shows the invoice summary and a Pay button", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/book/pay/i1"]}>
          <Routes>
            <Route path="/book/pay/:id" element={<PayInvoicePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText((content) => content.includes("INV-000001"))).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Pay with card/i })).toBeInTheDocument();
  });

  it("redirects to Razorpay payment link on click", async () => {
    const user = userEvent.setup();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/book/pay/i1"]}>
          <Routes>
            <Route path="/book/pay/:id" element={<PayInvoicePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
    await user.click(screen.getByRole("button", { name: /Pay with card/i }));
    expect(window.location.href).toBe("https://rzp.io/i/test");
  });
});
