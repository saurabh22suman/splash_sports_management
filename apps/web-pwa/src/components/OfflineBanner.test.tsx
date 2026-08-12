import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as offlineQueue from "../lib/offlineQueue";
import { OfflineBanner } from "./OfflineBanner";

// Mock the offline queue module
vi.mock("../lib/offlineQueue", () => ({
  getQueueLength: vi.fn(),
  drainQueue: vi.fn(),
  clearQueue: vi.fn(),
}));

describe("OfflineBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should not render when online and queue is empty", async () => {
    vi.mocked(offlineQueue.getQueueLength).mockResolvedValueOnce(0);

    // Mock navigator.onLine
    Object.defineProperty(navigator, "onLine", {
      value: true,
      writable: true,
    });

    render(<OfflineBanner />);

    await waitFor(() => {
      expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();
    });
  });

  it("should render when offline with items in queue", async () => {
    vi.mocked(offlineQueue.getQueueLength).mockResolvedValueOnce(3);

    // Mock navigator.onLine
    Object.defineProperty(navigator, "onLine", {
      value: false,
      writable: true,
    });

    render(<OfflineBanner />);

    await waitFor(() => {
      expect(screen.getByText(/3 booking.*pending/i)).toBeInTheDocument();
    });
  });

  it("should render when online but items in queue", async () => {
    vi.mocked(offlineQueue.getQueueLength).mockResolvedValueOnce(2);
    vi.mocked(offlineQueue.drainQueue).mockResolvedValueOnce({
      success: true,
      processedCount: 2,
    });

    // Mock navigator.onLine
    Object.defineProperty(navigator, "onLine", {
      value: true,
      writable: true,
    });

    render(<OfflineBanner />);

    await waitFor(() => {
      expect(screen.getByText(/2 booking.*pending/i)).toBeInTheDocument();
    });

    // Click retry button
    const retryButton = screen.getByText(/retry now/i);
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(offlineQueue.drainQueue).toHaveBeenCalled();
    });
  });

  it("should show success message after drain", async () => {
    vi.mocked(offlineQueue.getQueueLength).mockResolvedValueOnce(1);
    vi.mocked(offlineQueue.drainQueue).mockResolvedValueOnce({
      success: true,
      processedCount: 1,
    });

    Object.defineProperty(navigator, "onLine", {
      value: true,
      writable: true,
    });

    render(<OfflineBanner />);

    await waitFor(() => {
      expect(screen.getByText(/1 booking.*pending/i)).toBeInTheDocument();
    });

    // Click retry button
    const retryButton = screen.getByText(/retry now/i);
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText(/booking.*submitted/i)).toBeInTheDocument();
    });
  });
});
