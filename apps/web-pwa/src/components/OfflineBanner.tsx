import { useCallback, useEffect, useState } from "react";
import { type BookingInput, bookingsApi } from "../features/bookings/api";
import { drainQueue, getQueueLength } from "../lib/offlineQueue";

export function OfflineBanner() {
  const [queueLength, setQueueLength] = useState(0);
  const [isOnline, setIsOnline] = useState(true);
  const [showSuccess, setShowSuccess] = useState(false);
  const [isDraining, setIsDraining] = useState(false);

  const checkQueue = useCallback(async () => {
    try {
      const length = await getQueueLength();
      setQueueLength(length);
    } catch (error) {
      console.error("Failed to get queue length:", error);
    }
  }, []);

  const handleRetry = useCallback(async () => {
    if (isDraining || queueLength === 0) return;

    setIsDraining(true);
    try {
      const result = await drainQueue(async (input, _key) => {
        return bookingsApi.create(input as BookingInput);
      });

      if (result.success) {
        setShowSuccess(true);
        // Clear success message after 3 seconds
        setTimeout(() => {
          setShowSuccess(false);
        }, 3000);
        // Refresh queue length
        await checkQueue();
      }
    } catch (error) {
      console.error("Failed to drain queue:", error);
    } finally {
      setIsDraining(false);
    }
  }, [queueLength, isDraining, checkQueue]);

  useEffect(() => {
    // Check queue on mount and periodically
    checkQueue();

    const interval = setInterval(checkQueue, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, [checkQueue]);

  useEffect(() => {
    // Listen for online/offline events
    const handleOnline = () => {
      setIsOnline(true);
      // Auto-drain when coming back online
      if (queueLength > 0) {
        handleRetry();
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Set initial online status
    setIsOnline(navigator.onLine);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [queueLength, handleRetry]);

  // Don't render if no pending items and online
  if (queueLength === 0 && isOnline && !showSuccess) {
    return null;
  }

  // Show success message
  if (showSuccess) {
    return (
      <div
        role="alert"
        className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-success text-success-foreground px-4 py-2 rounded-md shadow-lg"
      >
        Your booking has been submitted successfully!
      </div>
    );
  }

  // Show offline/pending banner
  return (
    <div
      role="alert"
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-warning text-warning-foreground px-4 py-2 rounded-md shadow-lg flex items-center gap-3"
    >
      <span>
        {!isOnline && "You're offline. "}
        {queueLength > 0 && (
          <>
            {queueLength} booking{queueLength !== 1 ? "s" : ""} pending
            {!isOnline && " - will submit when online"}
          </>
        )}
      </span>
      {isOnline && queueLength > 0 && (
        <button
          onClick={handleRetry}
          disabled={isDraining}
          className="px-3 py-1 bg-warning-foreground text-warning rounded text-sm font-medium hover:opacity-90 disabled:opacity-50"
        >
          {isDraining ? "Submitting..." : "Retry now"}
        </button>
      )}
    </div>
  );
}
