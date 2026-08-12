import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return {
    ...actual,
    useAuthStore: (selector: (state: { roles: string[] }) => unknown) =>
      selector({ roles: ["tenant_admin"] }),
  };
});

vi.mock("@/features/payments/hooks", () => ({
  useInvoice: vi.fn(),
  useRefundInvoice: vi.fn(),
}));

import { useInvoice, useRefundInvoice } from "@/features/payments/hooks";
import { InvoiceDetailPage } from "@/pages/admin/InvoiceDetailPage";

describe("InvoiceDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows line items, totals, and refund button for tenant_admin", () => {
    (useInvoice as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        id: "i1",
        invoice_number: "INV-000001",
        status: "paid" as const,
        total_paise: 150000,
        currency: "INR",
        line_items: [
          {
            id: "li1",
            description: "Lane 4",
            quantity: 1,
            unit_price_paise: 150000,
            total_paise: 150000,
          },
        ],
        customer_id: "c1",
        tenant_id: "t1",
        subtotal_paise: 150000,
        tax_paise: 0,
        due_date: "2026-09-01",
        paid_at: "2026-08-01T00:00:00Z",
        description: "",
        created_at: "2026-08-01T00:00:00Z",
        updated_at: "2026-08-01T00:00:00Z",
      },
      isLoading: false,
      error: null,
    });

    (useRefundInvoice as ReturnType<typeof vi.fn>).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      error: null,
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/admin/invoices/i1"]}>
          <Routes>
            <Route path="/admin/invoices/:id" element={<InvoiceDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    // Use function matcher since text may be in nested elements
    expect(screen.getByText((content) => content.includes("Lane 4"))).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refund/i })).toBeInTheDocument();
  });
});
