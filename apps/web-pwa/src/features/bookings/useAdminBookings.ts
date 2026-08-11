import { useQuery } from "@tanstack/react-query";
import { bookingsApi, type Booking } from "./api";

export interface AdminBookingsParams {
  fromAt?: string;
  toAt?: string;
  facilityId?: string;
  resourceId?: string;
  status?: string[];
  limit?: number;
  offset?: number;
}

function buildAdminBookingsKey(params: AdminBookingsParams): string[] {
  const key = ["admin-bookings"];
  if (params.fromAt) key.push(`from:${params.fromAt}`);
  if (params.toAt) key.push(`to:${params.toAt}`);
  if (params.facilityId) key.push(`facility:${params.facilityId}`);
  if (params.resourceId) key.push(`resource:${params.resourceId}`);
  if (params.status?.length) key.push(`status:${params.status.join(",")}`);
  return key;
}

export function useAdminBookings(params: AdminBookingsParams = {}) {
  const { fromAt, toAt, facilityId, resourceId, status, limit = 100, offset = 0 } = params;

  return useQuery({
    queryKey: buildAdminBookingsKey(params),
    queryFn: () => bookingsApi.listAdmin(fromAt, toAt, facilityId, resourceId, status, limit, offset),
  });
}
