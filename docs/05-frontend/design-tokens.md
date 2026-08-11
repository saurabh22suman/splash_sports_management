# Design Tokens

> All tokens declared in `packages/ui/src/styles/globals.css` under `@theme`. Tailwind 4 generates utility classes from CSS variables. One file owns the palette.

Splashh uses a **two-layer token system** rather than the three-layer primitive → semantic → component model that's common in design systems. The reason: Tailwind 4's `@theme` directive already maps CSS variables to utilities, so we don't need a separate "primitive" layer — the raw values *are* the primitives.

```
Layer 1 (Primitives):  --color-charcoal-900: #0a0a0b     (raw values in @theme)
Layer 2 (Semantic):    --color-background: var(--color-charcoal-900)   (aliases for usage)
Layer 3 (Component):   n/a — components reference semantic utilities directly: bg-card, text-primary, …
```

---

## Where tokens live

A single file: [`packages/ui/src/styles/globals.css`](../../packages/ui/src/styles/globals.css). Apps import it via `@import "@splashh/ui/styles.css";`.

```css
/* packages/ui/src/styles/globals.css */
@import "tailwindcss";

@theme {
  /* Brand */
  --color-volt: #ccff00;
  --color-volt-hover: #b3e600;
  --color-volt-soft: #ccff001a;
  --color-accent-warm: #ff8a3d;
  --color-accent-warm-soft: #ff8a3d33;
  --color-accent-cool: #2bb1ff;

  /* Charcoal neutrals */
  --color-charcoal-50:  #f5f6f7;
  --color-charcoal-100: #e6e7eb;
  --color-charcoal-200: #c8cbd2;
  --color-charcoal-300: #a4a9b3;
  --color-charcoal-400: #7a808c;
  --color-charcoal-500: #555b66;
  --color-charcoal-600: #3a3f48;
  --color-charcoal-700: #2a2d34;
  --color-charcoal-800: #1d1f24;
  --color-charcoal-900: #0a0a0b;
  --color-charcoal-950: #050506;

  /* Semantic */
  --color-background: var(--color-charcoal-900);
  --color-foreground: #ffffff;
  --color-card: var(--color-charcoal-800);
  --color-card-foreground: #ffffff;
  --color-popover: var(--color-charcoal-800);
  --color-popover-foreground: #ffffff;
  --color-primary: var(--color-volt);
  --color-primary-hover: var(--color-volt-hover);
  --color-primary-foreground: #000000;
  --color-secondary: var(--color-charcoal-700);
  --color-secondary-foreground: #ffffff;
  --color-muted: var(--color-charcoal-700);
  --color-muted-foreground: var(--color-charcoal-300);
  --color-accent: var(--color-charcoal-700);
  --color-accent-foreground: #ffffff;
  --color-destructive: #ef4444;
  --color-destructive-foreground: #ffffff;
  --color-success: #22c55e;
  --color-success-foreground: #000000;
  --color-warning: #f59e0b;
  --color-warning-foreground: #000000;
  --color-border: var(--color-charcoal-600);
  --color-input: var(--color-charcoal-700);
  --color-ring: var(--color-volt);

  /* Typography */
  --font-sans: "Plus Jakarta Sans", system-ui, sans-serif;
  --font-display: "Oswald", "Plus Jakarta Sans", system-ui, sans-serif;
  --font-mono: ui-monospace, "SFMono-Regular", Menlo, monospace;

  /* Animations (sports-club motion vocabulary) */
  --animate-rise-up: rise-up 320ms cubic-bezier(0.16, 1, 0.3, 1) both;
  --animate-score-pop: score-pop 220ms cubic-bezier(0.16, 1, 0.3, 1) both;
  --animate-lane-glow: lane-glow 2.4s ease-in-out infinite;
  --animate-wave-drift: wave-drift 6s ease-in-out infinite;
  --animate-slide-in-left: slide-in-left 280ms cubic-bezier(0.16, 1, 0.3, 1) both;
  --animate-swim-bob: swim-bob 2.6s ease-in-out infinite;
  --animate-whistle: whistle 480ms cubic-bezier(0.16, 1, 0.3, 1) both;
  --animate-stroke: stroke 1.2s cubic-bezier(0.65, 0, 0.35, 1) both;
}
```

**That's the entire token system.** No `tailwind.config.ts`. No `tailwind-preset.ts`. No `postcss.config.js`. Tailwind 4's Vite plugin reads the `@theme` block and generates utilities.

---

## Layer 1 — Primitives

Raw values. The 9-step charcoal ramp + volt + accent-warm + accent-cool are the only color primitives. They're exposed as `bg-charcoal-{n}`, `text-charcoal-{n}`, etc.

Why no Tailwind `theme.extend.colors.blue.50` style primitives? Because we don't need them. The palette is intentionally narrow — anything outside the charcoal + volt + warm/cool accent palette is a design smell and should be flagged in review.

---

## Layer 2 — Semantic

Aliases for *where* a color is used, not *what* it is. `bg-card` doesn't tell you the color, it tells you the role. This is the only layer most components ever reference.

| Token | Resolves to | Used for |
|---|---|---|
| `bg-background` | `--color-charcoal-900` | page surface |
| `bg-card` | `--color-charcoal-800` | elevated surfaces (Card, Popover) |
| `bg-secondary` | `--color-charcoal-700` | hover / muted backgrounds |
| `bg-muted` | `--color-charcoal-700` | placeholders, skeletons |
| `text-foreground` | `#ffffff` | primary text |
| `text-muted-foreground` | `--color-charcoal-300` | secondary text, captions |
| `bg-primary` | `--color-volt` | primary CTA, active state |
| `text-primary` | `--color-volt` | brand emphasis |
| `border-border` | `--color-charcoal-600` | dividers, card outlines |
| `bg-destructive` | `#ef4444` | destructive actions |
| `bg-success` | `#22c55e` | confirmations |
| `bg-warning` | `#f59e0b` | past-due, attention |

If we ever ship a second tenant or a second theme, only the semantic layer changes — components don't.

---

## Layer 3 — Component

Tailwind 4 + `@theme` already gives us everything we need. Component-level wrappers (Button, Card, Input) live in `packages/ui` and apply semantic tokens via cva variants. **There is no separate component-token file.** If a component needs a one-off color, it should either:

1. Promote that color to a semantic token (preferred), or
2. Use an inline arbitrary value `[--my-color:#abc]` with a code-review comment explaining why it doesn't generalize.

---

## Naming conventions

- **Colors**: `--color-{name}-{step}` for ramps (charcoal-50…950), `--color-{name}` for one-offs (volt, accent-warm, accent-cool).
- **Semantic**: `--color-{role}` for surface/text/border, `--color-{role}-foreground` for ink on that surface (shadcn convention).
- **Fonts**: `--font-{family}` — `display` (Oswald), `sans` (Plus Jakarta Sans), `mono` (system mono).
- **Animations**: `--animate-{name}` where `{name}` is the keyframe name.
- **Keyframes**: `animation: {name} {duration}ms {easing} both` — declared alongside the `--animate-*` token in `@theme`.

---

## Adding a new token

1. Edit `packages/ui/src/styles/globals.css` and add the variable inside `@theme { … }`.
2. Restart Vite (`pnpm dev`) so the new utility classes are generated.
3. Reference it in components via the generated class (`bg-my-color`, `text-my-color`).
4. If it's a color meant for a specific role (e.g. "info"), add a semantic alias alongside it (`--color-info: var(--color-accent-cool)`).

**Don't:**
- Add raw hex values to component classNames.
- Define colors in JS/TS files.
- Create a separate `tokens.ts` that mirrors `globals.css`.

---

## Token reference

For an exhaustive list of every token currently exported, see the `@theme` block in [`packages/ui/src/styles/globals.css`](../../packages/ui/src/styles/globals.css). The file is the source of truth.

---

## Related documents

- [`theme-strategy.md`](./theme-strategy.md) — why single dark + volt, FOUC prevention, next-themes wiring
- [`component-design.md`](./component-design.md) — how primitives compose
