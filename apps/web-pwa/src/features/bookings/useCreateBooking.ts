import { useMutation, useQueryClient } from "@tanstack/react-query";
import { bookingsApi, type BookingInput } from "./api";
import { enqueueBooking, drainQueue, getQueueLength } from "../../lib/offlineQueue";
import { AxiosError } from "axios";

/**
 * Check if an error is a network error or 5xx server error
 */
function isRetryableError(error: unknown): boolean {
  if (error instanceof AxiosError) {
    // Network error (no response)
    if (!error.response) {
      return true;
    }
    // Server error (5xx)
    if (error.response.status >= 500 && error.response.status < 600) {
      return true;
    }
  }
  return false;
}

export interface CreateBookingResult {
  queued?: boolean;
  idempotencyKey?: string;
}

export function useCreateBooking() {
  const qc = useQueryClient();

  return useMutation<unknown, Error, BookingInput, CreateBookingResult>({
    mutationFn: async (input: BookingInput) => {
      try {
        return await bookingsApi.create(input);
      } catch (error) {
        // If retryable error, queue for later
        if (isRetryableError(error)) {
          const idempotencyKey = await enqueueBooking(input);
          return { queued: true, idempotencyKey };
        }
        // Re-throw non-retryable errors
        throw error;
      }
    },
    onSettled: (_data, _err, vars) => {
      qc.invalidateQueries({ queryKey: ["bookings", "by-resource", vars.resource_id] });
    },
  });
}

/**
 * Try to drain the offline queue - should be called on app load or network reconnect
 */
export async function tryDrainOfflineQueue(): Promise<{ success: boolean; processedCount: number }> {
  const queueLength = await getQueueLength();
  if (queueLength === 0) {
    return { success: true, processedCount: 0 };
  }

  const result = await drainQueue(async (input, _idempotencyKey) => {
    return bookingsApi.create(input as BookingInput);
  });

  return {
    success: result.success,
    processedCount: result.processedCount,
  };
}
