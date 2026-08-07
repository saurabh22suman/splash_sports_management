import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import "@testing-library/jest-dom/vitest";
import { LoadingSkeleton } from "./LoadingSkeleton";

describe("LoadingSkeleton", () => {
  it("renders a polite live region with screen-reader text", () => {
    render(<LoadingSkeleton />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveTextContent(/loading/i);
  });

  it("renders the requested number of lines", () => {
    const { container } = render(<LoadingSkeleton lines={5} />);
    expect(container.querySelectorAll("[data-skeleton-line]")).toHaveLength(5);
  });

  it("renders a card-shaped skeleton when withCard is true", () => {
    const { container } = render(<LoadingSkeleton withCard />);
    expect(container.querySelector("[data-skeleton-card]")).toBeInTheDocument();
  });
});
