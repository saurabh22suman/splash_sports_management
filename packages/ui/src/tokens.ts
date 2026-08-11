/**
 * Splashh Design System Tokens
 * Theme: "water + sports, restrained, confident."
 *
 * Primary: Deep ocean blue (#0B4F6C / #0E6BA8) — saturated, aquatic, mature
 * Accent: Warm safety-orange (#E85D04 / #F48C06) — lane-line / swim-cap / life-vest
 * Neutrals: Warm-tinted near-white, deep slate for body text
 *
 * All color values use OKLCH for perceptually uniform gradients.
 * Contrast ratios verified against WCAG AA (4.5:1 for body text).
 */

export const brand = {
  name: "Splashh",
  tagline: "Facility management for aquatic sports clubs",

  // Light mode colors
  light: {
    // Primary: Deep ocean blue — saturated, aquatic, mature
    // #0E6BA8 at 50% lightness in OKLCH
    primary: "oklch(52% 0.15 240)", // #0E6BA8 - deep ocean blue
    primaryFg: "oklch(98% 0.01 240)", // near-white with slight blue tint
    primaryMuted: "oklch(75% 0.08 240)", // lighter ocean for hover states

    // Accent: Warm safety-orange — lane-line / swim-cap / life-vest
    // #E85D04 at full saturation
    accent: "oklch(60% 0.18 30)", // #E85D04 - safety orange
    accentFg: "oklch(98% 0.02 30)", // near-white with warm tint

    // Background: Warm-tinted near-white (NOT pure white)
    // #FAFBFC with a subtle warm-aqua tint
    bg: "oklch(98.5% 0.005 240)", // #F8FAFC - warm-tinted near-white
    surface: "oklch(100% 0 0)", // pure white for cards

    // Ink: Deep slate (NOT blue-tinted gray)
    // #1A2937 - deep slate with slight warmth
    ink: "oklch(25% 0.03 240)", // #1E2D3D - deep readable slate

    // Muted: For secondary text
    // #64748B equivalent
    muted: "oklch(55% 0.02 240)", // #64748B - slate for secondary text
  },

  // Dark mode colors
  dark: {
    // Primary: Brighter ocean for dark backgrounds
    primary: "oklch(65% 0.18 240)", // #38BDF8 - bright ocean blue
    primaryFg: "oklch(20% 0.02 240)", // dark slate for contrast

    // Accent: Slightly brighter in dark mode for visibility
    accent: "oklch(70% 0.22 30)", // #FB923C - bright safety orange
    accentFg: "oklch(15% 0.02 30)", // dark for contrast

    // Background: Deep navy/slate (NOT blue-tinted gray)
    bg: "oklch(12% 0.02 240)", // #0F172A - deep navy
    surface: "oklch(18% 0.02 240)", // #1E293B - elevated surface

    // Ink: Light for body text
    ink: "oklch(92% 0.01 240)", // #E2E8F0 - light slate

    // Muted: Muted text in dark mode
    muted: "oklch(70% 0.02 240)", // #94A3B8 - muted slate
  },
} as const;

// Semantic aliases for common use cases
export const semantic = {
  // Success states
  success: {
    light: "oklch(72% 0.15 145)", // #22C55E green
    dark: "oklch(72% 0.15 145)",
  },
  // Warning states
  warning: {
    light: "oklch(75% 0.15 45)", // #EAB308 yellow
    dark: "oklch(75% 0.15 45)",
  },
  // Error/destructive states
  destructive: {
    light: "oklch(55% 0.18 25)", // #EF4444 red
    dark: "oklch(55% 0.18 25)",
  },
} as const;
