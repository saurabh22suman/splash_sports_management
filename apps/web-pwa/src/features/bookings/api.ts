import { api } from "@splashh/api-client";

export interface BookingInput {
  customer_id: string;
  resource_id: string;
  start_at: string;
  end_at: string;
  /** Note: price_cents is NOT sent - server computes from BookingTariff (F-05 fix) */
  notes?: string;
}
export interface Booking {
  id: string;
  tenant_id: string;
  customer_id: string;
  customer_name?: string | null; // Admin view only
  customer_email?: string | null; // Admin view only
  resource_id: string;
  facility_id?: string | null; // Admin view only
  facility_name?: string | null;
  resource_name?: string | null;
  start_at: string;
  end_at: string;
  status: "confirmed" | "cancelled" | "checked_in" | "completed" | "no_show";
  price_cents: number;
  currency: string;
  notes?: string | null;
  cancellation_reason?: string | null;
  cancelled_at?: string | null;
  checked_in_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export const bookingsApi = {
  create: (input: BookingInput) => api.post<Booking>("/booking", input).then((r) => r.data),
  listByResource: (resourceId: string, fromIso: string, toIso: string) =>
    api
      .get<{ data: Booking[] }>(`/booking/by-resource/${resourceId}`, {
        params: { from_at: fromIso, to_at: toIso },
      })
      .then((r) => r.data.data),
  listByCustomer: (customerId: string) =>
    api.get<{ data: Booking[] }>(`/booking/by-customer/${customerId}`).then((r) => r.data.data),
  listAdmin: (
    fromAt?: string,
    toAt?: string,
    facilityId?: string,
    resourceId?: string,
    status?: string[],
    limit?: number,
    offset?: number
  ) =>
    api
      .get<{ data: Booking[] }>("/booking/admin/bookings", {
        params: { from_at: fromAt, to_at: toAt, facility_id: facilityId, resource_id: resourceId, status, limit, offset },
      })
      .then((r) => r.data.data),
  get: (id: string) => api.get<Booking>(`/booking/${id}`).then((r) => r.data),
  cancel: (id: string, reason: string) =>
    api.post<Booking>(`/booking/${id}/cancel`, { reason }).then((r) => r.data),
};
