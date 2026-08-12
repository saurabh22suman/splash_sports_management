import { api } from "@splashh/api-client";
import type { Facility, Resource } from "@splashh/api-client";
export type { Facility, Resource } from "@splashh/api-client";

export interface FacilityInput {
  name: string;
  slug: string;
  address_line1?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  timezone: string;
  phone?: string;
}

export interface FacilityUpdateInput {
  name?: string;
  address_line1?: string;
  address_line2?: string | null;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  timezone?: string;
  phone?: string | null;
}

export interface ResourceInput {
  name: string;
  slug: string;
  resource_type: "court" | "lane" | "pool" | "field" | "net" | "studio" | "gym_floor" | "room";
  capacity: number;
  attributes?: Record<string, unknown>;
}

export interface ResourceUpdateInput {
  name?: string;
  capacity?: number;
  attributes?: Record<string, unknown>;
}

export const adminFacilitiesApi = {
  list: () => api.get<{ data: Facility[] }>("/facility").then((r) => r.data.data),
  get: (id: string) => api.get<Facility>(`/facility/${id}`).then((r) => r.data),
  create: (input: FacilityInput) => api.post<Facility>("/facility", input).then((r) => r.data),
  update: (id: string, input: FacilityUpdateInput) =>
    api.patch<Facility>(`/facility/${id}`, input).then((r) => r.data),
  deactivate: (id: string) => api.delete<void>(`/facility/${id}`).then(() => undefined),
  listResources: (facilityId: string) =>
    api.get<{ data: Resource[] }>(`/facility/${facilityId}/resources`).then((r) => r.data.data),
  createResource: (facilityId: string, input: ResourceInput) =>
    api.post<Resource>(`/facility/${facilityId}/resources`, input).then((r) => r.data),
  updateResource: (resourceId: string, input: ResourceUpdateInput) =>
    api.patch<Resource>(`/facility/resources/${resourceId}`, input).then((r) => r.data),
  deactivateResource: (resourceId: string) =>
    api.delete<void>(`/facility/resources/${resourceId}`).then(() => undefined),
};
