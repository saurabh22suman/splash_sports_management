import { queryKeys } from "@splashh/api-client";
import { useQuery } from "@tanstack/react-query";
import { bookingsApi } from "./api";

export function useBookingsByCustomer(customerId: string | null) {
  return useQuery({
    queryKey: customerId
      ? queryKeys.bookings.listByCustomer(customerId)
      : ["bookings", "by-customer", "none"],
    queryFn: () => bookingsApi.listByCustomer(customerId!),
    enabled: !!customerId,
  });
}
