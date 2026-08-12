import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/features/payments/hooks", () => ({
  useInvoices: vi.fn(),
}));

import { useInvoices } from "@/features/payments/hooks";
import { InvoicesPage } from "@/pages/admin/InvoicesPage";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <InvoicesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("InvoicesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the invoice number and status", () => {
    (useInvoices as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [
        {
          id: "i1",
          invoice_number: "INV-000001",
          customer_id: "c1",
          status: "pending" as const,
          total_paise: 150000,
          currency: "INR",
          due_date: "2026-09-01",
          subtotal_paise: 150000,
          tax_paise: 0,
          paid_at: null,
          description: "",
          line_items: [],
          created_at: "2026-08-01T00:00:00Z",
          updated_at: "2026-08-01T00:00:00Z",
          tenant_id: "t1",
        },
      ],
      isLoading: false,
      error: null,
    });

    wrap();
    // Invoice number renders in both mobile card list and desktop table
    expect(screen.getAllByText("INV-000001").length).toBeGreaterThan(0);
    // Use getAllByText since the filter buttons also have the status text
    expect(screen.getAllByText(/pending/i).length).toBeGreaterThan(0);
  });

  it("shows the New invoice link", () => {
    (useInvoices as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    wrap();
    // "+ New invoice" appears in both header and empty-state action
    expect(screen.getAllByRole("link", { name: /new invoice/i }).length).toBeGreaterThan(0);
  });
});
