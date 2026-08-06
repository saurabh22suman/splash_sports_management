import { api } from "@splashh/api-client";

export interface Facility {
  id: string;
  name: string;
  slug: string;
  address_line1: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  timezone: string;
  status: string;
}
export interface Resource {
  id: string;
  facility_id: string;
  name: string;
  slug: string;
  resource_type: string;
  capacity: number;
  attributes: Record<string, unknown> | null;
  status: string;
}

export const facilitiesApi = {
  list: () => api.get<{ data: Facility[] }>("/facility").then((r) => r.data.data),
  get: (id: string) => api.get<Facility>(`/facility/${id}`).then((r) => r.data),
  listResources: (facilityId: string) =>
    api.get<{ data: Resource[] }>(`/facility/${facilityId}/resources`).then((r) => r.data.data),
};
