import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(<EmptyState title="Nothing here" description="Try again later" />);
    expect(screen.getByRole("heading", { name: /nothing here/i })).toBeInTheDocument();
    expect(screen.getByText(/try again later/i)).toBeInTheDocument();
  });

  it("renders an onClick action as a button", () => {
    const onClick = vi.fn();
    render(<EmptyState title="Empty" action={{ label: "Refresh", onClick }} />);
    screen.getByRole("button", { name: /refresh/i }).click();
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("renders a `to` action as a link", () => {
    render(<EmptyState title="Empty" action={{ label: "Browse", to: "/book" }} />);
    const link = screen.getByRole("link", { name: /browse/i });
    expect(link).toHaveAttribute("href", "/book");
  });
});
