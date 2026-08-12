import type { BookingInput } from "../features/bookings/api";

const DB_NAME = "splash-offline-queue";
const STORE_NAME = "bookings";
const DB_VERSION = 1;

interface QueuedBooking {
  idempotencyKey: string;
  input: BookingInput;
  createdAt: number;
}

/**
 * Generate a deterministic idempotency key from booking input.
 * Uses JSON stringification of sorted keys for consistency.
 */
export function generateIdempotencyKey(input: BookingInput): string {
  // Create a stable string representation for deduplication
  const stableObj = {
    customer_id: input.customer_id,
    resource_id: input.resource_id,
    start_at: input.start_at,
    end_at: input.end_at,
  };
  return btoa(JSON.stringify(stableObj));
}

// Storage interface for abstraction (easier to mock in tests)
export interface StorageInterface {
  openDB(): Promise<IDBDatabase>;
}

// Default IndexedDB implementation
export const defaultStorage: StorageInterface = {
  async openDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: "idempotencyKey" });
        }
      };
    });
  },
};

// Current storage implementation (can be overridden for testing)
let storageImpl: StorageInterface = defaultStorage;

/**
 * Set the storage implementation (for testing)
 */
export function setStorageImpl(impl: StorageInterface): void {
  storageImpl = impl;
}

/**
 * Reset to default storage implementation
 */
export function resetStorageImpl(): void {
  storageImpl = defaultStorage;
}

/**
 * Get the queue length (number of pending bookings)
 */
export async function getQueueLength(): Promise<number> {
  const db = await storageImpl.openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const countRequest = store.count();

    countRequest.onsuccess = () => resolve(countRequest.result);
    countRequest.onerror = () => reject(countRequest.error);
  });
}

/**
 * Get all queued bookings
 */
async function getAllQueued(): Promise<QueuedBooking[]> {
  const db = await storageImpl.openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const getAllRequest = store.getAll();

    getAllRequest.onsuccess = () => resolve(getAllRequest.result);
    getAllRequest.onerror = () => reject(getAllRequest.error);
  });
}

/**
 * Add a booking to the offline queue.
 * Returns the idempotency key used.
 */
export async function enqueueBooking(input: BookingInput): Promise<string> {
  const idempotencyKey = generateIdempotencyKey(input);
  const db = await storageImpl.openDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);

    // Check if already exists (dedupe)
    const getRequest = store.get(idempotencyKey);

    getRequest.onsuccess = () => {
      if (getRequest.result) {
        // Already exists, return existing key
        resolve(idempotencyKey);
        return;
      }

      // Add new item
      const queuedBooking: QueuedBooking = {
        idempotencyKey,
        input,
        createdAt: Date.now(),
      };

      const putRequest = store.put(queuedBooking);
      putRequest.onsuccess = () => resolve(idempotencyKey);
      putRequest.onerror = () => reject(putRequest.error);
    };

    getRequest.onerror = () => reject(getRequest.error);
  });
}

/**
 * Fetch a single queued booking and remove it from the queue
 */
async function popOne(idempotencyKey: string): Promise<QueuedBooking | null> {
  const db = await storageImpl.openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const getRequest = store.get(idempotencyKey);

    getRequest.onsuccess = () => {
      const result = getRequest.result as QueuedBooking | undefined;
      if (result) {
        // Remove after fetching
        store.delete(idempotencyKey);
      }
      resolve(result || null);
    };

    getRequest.onerror = () => reject(getRequest.error);
  });
}

/**
 * Drain the queue by calling the fetcher for each item in FIFO order.
 * Stops on first failure.
 */
export async function drainQueue(
  fetcher: (input: BookingInput, idempotencyKey: string) => Promise<unknown>,
): Promise<{ success: boolean; processedCount: number; error?: Error }> {
  const queued = await getAllQueued();

  // Sort by createdAt for FIFO order
  queued.sort((a, b) => a.createdAt - b.createdAt);

  let processedCount = 0;

  for (const item of queued) {
    try {
      await fetcher(item.input, item.idempotencyKey);
      // Remove from queue on success
      await popOne(item.idempotencyKey);
      processedCount++;
    } catch (error) {
      // Stop on first failure - leave remaining items in queue
      return {
        success: false,
        processedCount,
        error: error instanceof Error ? error : new Error(String(error)),
      };
    }
  }

  return { success: true, processedCount };
}

/**
 * Clear all queued bookings
 */
export async function clearQueue(): Promise<void> {
  const db = await storageImpl.openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const clearRequest = store.clear();

    clearRequest.onsuccess = () => resolve();
    clearRequest.onerror = () => reject(clearRequest.error);
  });
}

/**
 * Get the offline queue instance for external use (e.g., to check if there are pending items)
 */
export async function getOfflineQueue() {
  return getAllQueued();
}
