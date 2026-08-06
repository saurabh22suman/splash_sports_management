# @splashh/ui

Shared UI primitives for the Splashh Sports Platform. Brand-themed shadcn/ui
components, built on Radix, Tailwind, and the `@splashh/ui/tailwind-preset`
design tokens.

## Install

Already wired into the workspace as `"@splashh/ui": "workspace:*"`. In a new
app: `pnpm add @splashh/ui @splashh/config`.

## Usage

```ts
import { Button, Card, FormField, Input, brand } from "@splashh/ui";
import "@splashh/ui/styles.css";
```

Wire the tailwind preset in your `tailwind.config.ts`:

```ts
import splashhPreset from "@splashh/ui/tailwind-preset";
export default { presets: [splashhPreset], content: ["./src/**/*.{ts,tsx}"] };
```

## Add a new shadcn primitive

```bash
pnpm ui:add dialog
```

This scopes the shadcn CLI to `packages/ui` per the root `ui:add` script.

## Test

```bash
pnpm --filter @splashh/ui test
```

## Coverage

≥80% (lines, functions, statements) per the Vite config thresholds.
