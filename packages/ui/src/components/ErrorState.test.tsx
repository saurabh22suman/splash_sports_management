import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  it("renders an alert role with default title", () => {
    render(<ErrorState />);
    expect(screen.getByRole("alert")).toHaveTextContent(/something went wrong/i);
  });

  it("renders a retry button when onRetry is provided", () => {
    const onRetry = vi.fn();
    render(<ErrorState onRetry={onRetry} />);
    screen.getByRole("button", { name: /retry/i }).click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("uses a custom title and description when provided", () => {
    render(<ErrorState title="Could not load" description="Network error" />);
    expect(screen.getByRole("alert")).toHaveTextContent(/could not load/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/network error/i);
  });
});
