// Hand-written domain types shared by the PWAs. Once we wire up OpenAPI
// generation (see spec §5), these become re-exports of the generated types.

export interface Facility {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  timezone: string;
  phone: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Resource {
  id: string;
  tenant_id: string;
  facility_id: string;
  name: string;
  slug: string;
  resource_type: string;
  capacity: number;
  attributes: Record<string, unknown> | null;
  status: string;
  created_at: string;
  updated_at: string;
}
