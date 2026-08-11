/**
 * Test for OpenAPI TypeScript code generation.
 *
 * This test verifies that the codegen script correctly converts an OpenAPI schema
 * into TypeScript types.
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

describe("codegen", () => {
  const fixturePath = resolve(__dirname, "./fixtures/openapi.json");
  const outputPath = resolve(
    __dirname,
    "../../../packages/api-client/src/types/generated.ts"
  );

  it("generates TypeScript types from OpenAPI schema", async () => {
    // Read the fixture
    const openapiJson = JSON.parse(readFileSync(fixturePath, "utf-8"));

    // Import and run the generator
    const { generateTypes } = await import("./generate-types.js");
    const generated = generateTypes(openapiJson);

    // Verify key types are generated
    expect(generated).toContain("export interface FacilityOut");
    expect(generated).toContain("export interface ResourceOut");
    expect(generated).toContain("export interface BookingOut");
    expect(generated).toContain("export interface FacilityListResponse");
    expect(generated).toContain("export interface BookingListResponse");

    // Verify UUID types are handled
    expect(generated).toContain("id: string");

    // Verify date-time formats are handled
    expect(generated).toContain("created_at: string");
    expect(generated).toContain("start_at: string");
    expect(generated).toContain("end_at: string");

    // Verify nullable fields
    expect(generated).toContain("address_line2?: string | null");
    expect(generated).toContain("phone?: string | null");

    // Verify required vs optional
    expect(generated).toContain("name: string"); // required
  });
});
