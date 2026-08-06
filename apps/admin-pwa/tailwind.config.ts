import type { Config } from "tailwindcss";
import splashhPreset from "@splashh/ui/tailwind-preset";

export default {
  presets: [splashhPreset],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
} satisfies Config;
