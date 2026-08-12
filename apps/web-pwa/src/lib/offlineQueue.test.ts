import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type StorageInterface,
  clearQueue,
  drainQueue,
  enqueueBooking,
  getOfflineQueue,
  getQueueLength,
  resetStorageImpl,
  setStorageImpl,
} from "./offlineQueue";

// In-memory storage implementation for testing
class InMemoryStorage implements StorageInterface {
  private store: Map<string, { idempotencyKey: string; input: unknown; createdAt: number }> =
    new Map();
  private dbOpened = false;

  async openDB(): Promise<IDBDatabase> {
    this.dbOpened = true;

    // Create a mock IDBDatabase
    const mockDB = {
      objectStoreNames: {
        contains: (name: string) => name === "bookings",
      },
      transaction: (stores: string[], mode: IDBTransactionMode) => {
        return {
          objectStore: (storeName: string) => {
            return {
              get: (key: string) => this.createRequest(this.store.get(key)),
              getAll: () => this.createRequest(Array.from(this.store.values())),
              put: (value: { idempotencyKey: string; input: unknown; createdAt: number }) => {
                this.store.set(value.idempotencyKey, value);
                return this.createRequest(value);
              },
              delete: (key: string) => {
                this.store.delete(key);
                return this.createRequest(undefined);
              },
              clear: () => {
                this.store.clear();
                return this.createRequest(undefined);
              },
              count: () => this.createRequest(this.store.size),
            };
          },
        };
      },
      close: () => {},
      createObjectStore: () => {},
    } as unknown as IDBDatabase;

    return Promise.resolve(mockDB);
  }

  private createRequest<T>(result: T): IDBRequest<T> {
    let successHandler: ((e: Event) => void) | null = null;
    let errorHandler: ((e: Event) => void) | null = null;

    const request = {
      result,
      onsuccess: null,
      onerror: null,
    } as unknown as IDBRequest<T>;

    // Use a custom setter to trigger the handler
    Object.defineProperty(request, "onsuccess", {
      set(handler) {
        successHandler = handler;
        // Trigger asynchronously
        Promise.resolve().then(() => {
          if (successHandler) {
            successHandler({} as Event);
          }
        });
      },
      get() {
        return successHandler;
      },
    });

    Object.defineProperty(request, "onerror", {
      set(handler) {
        errorHandler = handler;
      },
      get() {
        return errorHandler;
      },
    });

    return request;
  }
}

describe("offlineQueue", () => {
  let memoryStorage: InMemoryStorage;

  beforeEach(() => {
    memoryStorage = new InMemoryStorage();
    setStorageImpl(memoryStorage);
  });

  afterEach(() => {
    resetStorageImpl();
  });

  describe("enqueueBooking", () => {
    it("should enqueue a booking request with idempotency key", async () => {
      const bookingInput = {
        customer_id: "cust-123",
        resource_id: "res-456",
        start_at: "2024-01-01T10:00:00Z",
        end_at: "2024-01-01T12:00:00Z",
      };

      const idempotencyKey = await enqueueBooking(bookingInput);

      expect(idempotencyKey).toBeDefined();
      expect(typeof idempotencyKey).toBe("string");

      const length = await getQueueLength();
      expect(length).toBe(1);
    });

    it("should dedupe by idempotency key (same input = same key)", async () => {
      const bookingInput = {
        customer_id: "cust-123",
        resource_id: "res-456",
        start_at: "2024-01-01T10:00:00Z",
        end_at: "2024-01-01T12:00:00Z",
      };

      const key1 = await enqueueBooking(bookingInput);
      const key2 = await enqueueBooking(bookingInput);

      // Same input should generate same idempotency key
      expect(key1).toBe(key2);

      // But should only be stored once (dedupe)
      const length = await getQueueLength();
      expect(length).toBe(1);
    });

    it("should allow different bookings with different inputs", async () => {
      const booking1 = {
        customer_id: "cust-123",
        resource_id: "res-456",
        start_at: "2024-01-01T10:00:00Z",
        end_at: "2024-01-01T12:00:00Z",
      };

      const booking2 = {
        customer_id: "cust-789",
        resource_id: "res-456",
        start_at: "2024-01-01T14:00:00Z",
        end_at: "2024-01-01T16:00:00Z",
      };

      await enqueueBooking(booking1);
      await enqueueBooking(booking2);

      const length = await getQueueLength();
      expect(length).toBe(2);
    });
  });

  describe("getQueueLength", () => {
    it("should return 0 for empty queue", async () => {
      const length = await getQueueLength();
      expect(length).toBe(0);
    });

    it("should return correct count after enqueuing", async () => {
      await enqueueBooking({
        customer_id: "cust-1",
        resource_id: "res-1",
        start_at: "2024-01-01T10:00:00Z",
        end_at: "2024-01-01T12:00:00Z",
      });
      await enqueueBooking({
        customer_id: "cust-2",
        resource_id: "res-2",
        start_at: "2024-01-01T14:00:00Z",
        end_at: "2024-01-01T16:00:00Z",
      });

      const length = await getQueueLength();
      expect(length).toBe(2);
    });
  });

  describe("drainQueue", () => {
    it("should drain queue in order (FIFO)", async () => {
      const calls: Array<{ input: unknown; key: string }> = [];

      const mockFetcher = vi.fn(async (input: unknown, key: string) => {
        calls.push({ input, key });
        return { success: true };
      });

      await enqueueBooking({
        customer_id: "cust-1",
        resource_id: "res-1",
        start_at: "2024-01-01T10:00:00Z",
        end_at: "2024-01-01T12:00:00Z",
      });

      await enqueueBooking({
        customer_id: "cust-2",
        resource_id: "res-2",
        start_at: "2024-01-01T14:00:00Z",
        end_at: "2024-01-01T16:00:00Z",
      });

      await drainQueue(mockFetcher);

      expect(mockFetcher).toHaveBeenCalledTimes(2);
      expect(calls[0]?.input).toMatchObject({ customer_id: "cust-1" });
      expect(calls[1]?.input).toMatchObject({ customer_id: "cust-2" });
    });

    it("should remove items from queue after successful drain", async () => {
      const mockFetcher = vi.fn(async () => ({ success: true }));

      await enqueueBooking({
        customer_id: "cust-1",
        resource_id: "res-1",
        start_at: "2024-01-01T10:00:00Z",
        end_at: "2024-01-01T12:00:00Z",
      });

      await drainQueue(mockFetcher);

      const length = await getQueueLength();
      expect(length).toBe(0);
    });

    it("should stop on failure and keep remaining items", async () => {
      const mockFetcher = vi
        .fn()
        .mockResolvedValueOnce({ success: true })
        .mockRejectedValueOnce(new Error("Network error"));

      await enqueueBooking({
        customer_id: "cust-1",
        resource_id: "res-1",
        start_at: "2024-01-01T10:00:00Z",
        end_at: "2024-01-01T12:00:00Z",
      });

      await enqueueBooking({
        customer_id: "cust-2",
        resource_id: "res-2",
        start_at: "2024-01-01T14:00:00Z",
        end_at: "2024-01-01T16:00:00Z",
      });

      await drainQueue(mockFetcher);

      // Only first should succeed, second fails so stays in queue
      expect(mockFetcher).toHaveBeenCalledTimes(2);

      const length = await getQueueLength();
      expect(length).toBe(1);
    });

    it("should handle empty queue gracefully", async () => {
      const mockFetcher = vi.fn();

      await drainQueue(mockFetcher);

      expect(mockFetcher).not.toHaveBeenCalled();
    });
  });

  describe("clearQueue", () => {
    it("should clear all queued items", async () => {
      await enqueueBooking({
        customer_id: "cust-1",
        resource_id: "res-1",
        start_at: "2024-01-01T10:00:00Z",
        end_at: "2024-01-01T12:00:00Z",
      });

      await clearQueue();

      const length = await getQueueLength();
      expect(length).toBe(0);
    });
  });
});
