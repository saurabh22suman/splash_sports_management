// Re-export generated types from OpenAPI schema.
// The hand-written types below are kept for backward compatibility but should
// be phased out in favor of the auto-generated types.
//
// Once we wire up OpenAPI generation (see spec §5), these become re-exports
// of the generated types.

// Re-export all generated types
export * from "./generated";

// Legacy hand-written types (deprecated - use generated types instead)
// These are kept for backward compatibility with existing code that imports from domain.ts

/** @deprecated Use FacilityOut from generated.ts */
export type Facility = import("./generated").FacilityOut;

/** @deprecated Use ResourceOut from generated.ts */
export type Resource = import("./generated").ResourceOut;
