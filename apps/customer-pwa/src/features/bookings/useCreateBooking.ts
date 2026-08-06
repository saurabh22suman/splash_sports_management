import { useMutation, useQueryClient } from "@tanstack/react-query";
import { bookingsApi, type BookingInput } from "./api";

export function useCreateBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: BookingInput) => bookingsApi.create(input),
    onSettled: (_data, _err, vars) => {
      qc.invalidateQueries({ queryKey: ["bookings", "by-resource", vars.resource_id] });
    },
  });
}
