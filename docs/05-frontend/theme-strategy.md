# Theme Strategy

> Single dark + volt athletic palette via Tailwind 4 `@theme`. Dark mode class wired with `next-themes`. Persisted preference. No FOUC.

Splashh commits to one theme: **dark surface, volt (#CCFF00) accent, charcoal neutrals**. No light/dark toggle. Every page, modal and component renders against `#0a0a0b` page, `#1d1f24` cards, with `#CCFF00` for primary actions and active states. Fonts are **Oswald** (display, uppercase headlines) + **Plus Jakarta Sans** (body).

This is an intentional choice for a sports-club product targeting pool / court / gym operators — the brand reads as athletic, the contrast reads as a control panel, not a SaaS marketing page.

---

## Token location

All design tokens live in **one place**: [`packages/ui/src/styles/globals.css`](../../packages/ui/src/styles/globals.css), inside a single `@theme { … }` block. Apps import this stylesheet directly:

```css
/* apps/web-pwa/src/styles/globals.css */
@import "@splashh/ui/styles.css";
```

The `@theme` directive tells Tailwind 4 to expose every `--color-*`, `--font-*`, `--animate-*`, and `--radius-*` variable as a utility class. Adding `--color-volt: #ccff00` is enough to generate `bg-volt`, `text-volt`, `border-volt`, etc.

```css
/* packages/ui/src/styles/globals.css */
@theme {
  --color-volt: #ccff00;
  --color-volt-hover: #b3e600;

  --color-charcoal-900: #0a0a0b;
  --color-charcoal-800: #1d1f24;
  --color-charcoal-700: #2a2d34;
  --color-charcoal-600: #3a3f48;
  --color-charcoal-300: #a4a9b3;

  --color-background: var(--color-charcoal-900);
  --color-foreground: #ffffff;
  --color-card: var(--color-charcoal-800);
  --color-card-foreground: #ffffff;
  --color-muted: var(--color-charcoal-700);
  --color-muted-foreground: var(--color-charcoal-300);
  --color-border: var(--color-charcoal-600);

  --font-display: "Oswald", "Plus Jakarta Sans", system-ui, sans-serif;
  --font-sans: "Plus Jakarta Sans", system-ui, sans-serif;

  --animate-rise-up: rise-up 320ms cubic-bezier(0.16, 1, 0.3, 1) both;
  --animate-score-pop: score-pop 220ms cubic-bezier(0.16, 1, 0.3, 1) both;
  /* … */
}
```

There is **no `tailwind.config.ts`**, **no `tailwind-preset.ts`**, and **no `postcss.config.js`** — Tailwind 4's Vite plugin reads tokens directly from CSS.

---

## Why this approach

### Tailwind 4 `@theme` instead of a JS config

Tailwind 4 moves configuration into CSS, so:

- Tokens are visible in the same file as the styles that consume them.
- Adding `--color-accent-warm` generates `bg-accent-warm` / `text-accent-warm` automatically.
- No build step needed for token additions.

### Single dark theme

- A sports-club operator lives in fluorescent-lit front-of-house with a phone. Dark UI reduces glare and reads as a control panel, not a marketing page.
- We avoid the "light mode looks fine in the screenshot but breaks in prod" problem by not shipping it.
- The volt accent (#CCFF00) is high-contrast on charcoal-900 — passes WCAG AA for large text and for icon / button labels.

### Semantic tokens (`bg-card`, `text-foreground`, etc.)

Component code uses semantic tokens, not raw colors:

```tsx
// ✅ preferred — works across themes / refactors
<div className="bg-card text-card-foreground border border-border">

// ❌ avoided — bypasses the system
<div className="bg-[#1d1f24] text-white border-[#3a3f48]">
```

This is enforced by code review: any PR that adds raw hex / arbitrary Tailwind colors to a component is rejected.

---

## Dark mode provider

We use [`next-themes`](https://github.com/pacocoursey/next-themes) for class-on-`<html>` management. Even though we ship one theme, the `class="dark"` attribute lets us test dark-vs-system-contrast regressions and leaves the door open for a light variant without touching components.

```tsx
// apps/web-pwa/src/main.tsx
import { ThemeProvider } from "next-themes";
import App from "./App";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
```

Settings:
- `attribute="class"` — applies `class="dark"` to `<html>` (Tailwind's class strategy).
- `defaultTheme="dark"` — never flashes light.
- `enableSystem={false}` — system-preference auto-switch is intentionally disabled (we commit to dark).

---

## Preventing flash of unstyled content (FOUC)

The `<html>` element ships with `class="dark"` set inline in `apps/web-pwa/index.html` so the page paints dark before React hydrates:

```html
<html lang="en" class="dark">
```

No inline script needed — `class="dark"` is rendered server-side (or statically for the SPA shell).

---

## Adding a new token

To add a brand color or animation, edit `packages/ui/src/styles/globals.css`:

```css
@theme {
  --color-pool-blue: #2bb1ff;   /* generates bg-pool-blue, text-pool-blue, … */
}
```

Restart Vite (`pnpm dev`) — the new utility classes are generated on the next build. No config files to edit.

If you need a new token that should NOT become a utility (e.g. an internal spacing rhythm), put it under `@layer base` or as a plain CSS variable outside `@theme`:

```css
@layer base {
  :root {
    --internal-rhythm: 1.5rem;
  }
}
```

---

## Tenant theming (future)

Per-tenant colors are not yet supported. The intended path: pull `--color-volt` and `--color-volt-hover` from a `/v1/tenant/theme` endpoint, set them on `:root` via inline `<style>` after login. Components don't need to change because they reference `bg-primary` / `text-primary`, which resolve through the cascade.

---

## Related documents

- [`design-tokens.md`](./design-tokens.md) — token architecture, primitive → semantic → component layers
- [`component-design.md`](./component-design.md) — how primitives compose against the theme
- [Tailwind 4 theme variables](https://tailwindcss.com/docs/theme) — official reference
