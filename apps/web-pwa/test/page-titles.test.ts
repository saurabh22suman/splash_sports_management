import { describe, expect, it } from "vitest";
import { titleForPath } from "@/lib/page-titles";

describe("titleForPath", () => {
  it("returns the public landing title at /", () => {
    expect(titleForPath("/")).toBe("Splashh");
  });

  it("returns the customer login title at /login", () => {
    expect(titleForPath("/login")).toBe("Splashh · Log in");
  });

  it("returns the admin login title at /admin/login", () => {
    expect(titleForPath("/admin/login")).toBe("Splashh Admin");
  });

  it("returns the admin facilities title at /admin", () => {
    expect(titleForPath("/admin")).toBe("Splashh Admin · Facilities");
  });

  it("returns the admin users title at /admin/users", () => {
    expect(titleForPath("/admin/users")).toBe("Splashh Admin · Users");
  });

  it("returns the new facility title at /admin/facilities/new", () => {
    expect(titleForPath("/admin/facilities/new")).toBe("Splashh Admin · New facility");
  });

  it("returns the facility detail title at /admin/facilities/:id", () => {
    expect(titleForPath("/admin/facilities/abc-123")).toBe("Splashh Admin · Facility");
  });

  it("returns the customer facilities title at /book", () => {
    expect(titleForPath("/book")).toBe("Splashh · Facilities");
  });

  it("returns the customer bookings title at /book/bookings", () => {
    expect(titleForPath("/book/bookings")).toBe("Splashh · My bookings");
  });

  it("returns the customer facility detail title at /book/facilities/:id", () => {
    expect(titleForPath("/book/facilities/abc-123")).toBe("Splashh · Facility details");
  });

  it("falls back to the default title for unknown paths", () => {
    expect(titleForPath("/whatever/else")).toBe("Splashh");
  });
});
