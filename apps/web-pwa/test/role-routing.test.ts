import { describe, expect, it } from "vitest";
import { homeForRoles } from "../src/lib/role-routing";

describe("homeForRoles", () => {
  it("admin goes to /admin", () => {
    expect(homeForRoles(["tenant_admin"])).toBe("/admin");
  });
  it("customer goes to /book", () => {
    expect(homeForRoles(["customer"])).toBe("/book");
  });
  it("staff goes to /staff", () => {
    expect(homeForRoles(["staff"])).toBe("/staff");
  });
  it("empty falls back to /", () => {
    expect(homeForRoles([])).toBe("/");
  });
  it("admin wins over customer if both present", () => {
    expect(homeForRoles(["customer", "tenant_admin"])).toBe("/admin");
  });
});
