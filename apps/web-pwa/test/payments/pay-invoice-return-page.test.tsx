import { describe, it, expect, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/features/payments/hooks", () => ({
  useInvoice: vi.fn(),
}));

import { useInvoice } from "@/features/payments/hooks";
import { PayInvoiceReturnPage } from "@/pages/book/PayInvoiceReturnPage";

function wrap(status: string) {
  (useInvoice as ReturnType<typeof vi.fn>).mockReturnValue({
    data: { status, invoice_number: "INV-000001" },
    isLoading: false,
    refetch: vi.fn(),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/book/pay/i1/return"]}>
        <Routes>
          <Route path="/book/pay/:id/return" element={<PayInvoiceReturnPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("PayInvoiceReturnPage", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows success state when invoice is paid", () => {
    wrap("paid");
    expect(screen.getByText(/Payment successful/i)).toBeInTheDocument();
  });
  it("shows processing state otherwise", () => {
    wrap("pending");
    expect(screen.getByText(/Processing/i)).toBeInTheDocument();
  });
});
