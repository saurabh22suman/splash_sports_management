export const queryKeys = {
  facilities: {
    all: ["facilities"] as const,
    list: (tenantId: string) => ["facilities", "list", tenantId] as const,
    detail: (id: string) => ["facilities", "detail", id] as const,
  },
  resources: {
    listByFacility: (facilityId: string) => ["resources", "by-facility", facilityId] as const,
  },
  availability: {
    listByResource: (resourceId: string) => ["availability", "by-resource", resourceId] as const,
  },
  bookings: {
    listByResource: (resourceId: string, fromIso: string, toIso: string) =>
      ["bookings", "by-resource", resourceId, fromIso, toIso] as const,
    listByCustomer: (customerId: string) => ["bookings", "by-customer", customerId] as const,
    detail: (id: string) => ["bookings", "detail", id] as const,
  },
  customers: {
    list: (tenantId: string) => ["customers", "list", tenantId] as const,
    detail: (id: string) => ["customers", "detail", id] as const,
  },
} as const;
