# Frontend PWAs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold `admin-pwa`, `customer-pwa`, and shared `@splashh/*` packages; add httpOnly refresh-cookie support to the backend; deliver a working thin slice in each PWA against the live backend.

**Architecture:** pnpm workspace with two Vite React apps and three shared packages (`@splashh/ui`, `@splashh/api-client`, `@splashh/config`). Silent-refresh auth via a single-flight axios interceptor backed by an httpOnly refresh cookie set by the backend. TanStack Query for server state, Zustand for auth singleton, React Router v6 data router with lazy chunks, vite-plugin-pwa (Workbox) for install + offline.

**Tech Stack:** Vite 5, React 18, TypeScript 5.6, Tailwind 3, shadcn/ui, Radix primitives, TanStack Query v5, React Router v6, React Hook Form, Zod, Zustand, axios, vite-plugin-pwa, Biome, Vitest + RTL + happy-dom, Playwright + axe-core, MSW.

**Spec:** `docs/superpowers/specs/2026-08-06-frontend-pwas-design.md`

## Global Constraints

- All paths in this plan are relative to the repo root `splash_sports_management/`.
- Backend tests use `uv run pytest` from `apps/backend/`. Frontend tests use `pnpm test` from each package.
- Backend dev port: **8765**. Admin PWA: **5173**. Customer PWA: **5174**. Vite proxy: `/v1` → `http://127.0.0.1:8765`.
- Cookie attrs on refresh: `HttpOnly; SameSite=Lax; Path=/v1/auth; Max-Age=2592000`. `Secure` ON in prod, OFF in dev.
- Brand color: light `#0EA5E9` (sky-500), dark `#38BDF8` (sky-400).
- Access token TTL: shortened to **5 min (300s)**. Refresh token TTL: **30 days (2592000s)**, unchanged.
- Every task ends with a `git commit` and a verification command that an engineer can re-run.
- No `localStorage` for tokens. Access token lives in a Zustand store (in-memory).
- `package.json` scripts follow the table in spec §11.
- `next-themes` is the theme lib (despite the name, it works in Vite — set `attribute="class"`).
- shadcn primitives are generated with `pnpm dlx shadcn@latest add <name>` from inside `packages/ui/`.

---

## Phase 0 — Workspace Scaffolding

### Task 1: pnpm workspace + root config

**Files:**
- Create: `pnpm-workspace.yaml`
- Create: `package.json` (root)
- Create: `.npmrc`
- Create: `tsconfig.base.json`
- Create: `biome.json`
- Create: `.gitignore` (append)
- Create: `apps/backend/Makefile`

**Interfaces:**
- Consumes: nothing
- Produces: `pnpm install` works at root; `pnpm -r typecheck` exits 0; `make -C apps/backend dev` starts uvicorn on 8765

- [ ] **Step 1: Verify pnpm is installed**

Run: `which pnpm && pnpm --version`
Expected: prints a path and version ≥ 9.0. If missing, install: `npm install -g pnpm@9`.

- [ ] **Step 2: Create `pnpm-workspace.yaml`**

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 3: Create root `package.json`**

```json
{
  "name": "splashh-monorepo",
  "private": true,
  "version": "0.1.0",
  "engines": { "node": ">=20", "pnpm": ">=9" },
  "scripts": {
    "dev": "concurrently -k -n backend,admin,customer -c blue,magenta,green \"make -C apps/backend dev\" \"pnpm --filter admin-pwa dev\" \"pnpm --filter customer-pwa dev\"",
    "build": "pnpm -r build",
    "typecheck": "pnpm -r typecheck",
    "lint": "biome check .",
    "lint:fix": "biome check --write .",
    "test": "pnpm -r test",
    "test:e2e": "playwright test",
    "ui:add": "pnpm --filter @splashh/ui dlx shadcn@latest add"
  },
  "devDependencies": {
    "@biomejs/biome": "^1.9.0",
    "concurrently": "^9.0.0"
  }
}
```

- [ ] **Step 4: Create `.npmrc`**

```
node-linker=hoisted
auto-install-peers=true
strict-peer-dependencies=false
```

`node-linker=hoisted` is required so Vite resolves workspace symlinks without extra plugin config.

- [ ] **Step 5: Create `tsconfig.base.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": false,
    "allowSyntheticDefaultImports": true
  }
}
```

- [ ] **Step 6: Create `biome.json`**

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.0/schema.json",
  "vcs": { "enabled": true, "clientKind": "git", "useIgnoreFile": true },
  "files": { "ignoreUnknown": true, "ignore": ["**/dist/**", "**/node_modules/**", "**/.venv/**"] },
  "formatter": { "enabled": true, "indentStyle": "space", "indentWidth": 2, "lineWidth": 100 },
  "organizeImports": { "enabled": true },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "style": { "noNonNullAssertion": "warn" },
      "suspicious": { "noExplicitAny": "warn" }
    }
  },
  "javascript": { "formatter": { "quoteStyle": "double", "semicolons": "always", "trailingCommas": "all" } }
}
```

- [ ] **Step 7: Append to `.gitignore`**

```
# Frontend
node_modules/
dist/
.pnpm-store/
.vite/
*.tsbuildinfo
playwright-report/
test-results/
coverage/
.env.local
```

- [ ] **Step 8: Create `apps/backend/Makefile`**

```makefile
.PHONY: dev test

dev:
	PYTHONPATH=src ENVIRONMENT=development DEBUG=false \
	JWT_ALGORITHM=HS256 \
	JWT_SECRET="dev-only-jwt-secret-change-me-in-prod-please-32chars" \
	uv run uvicorn common.interfaces.http.app:create_app --factory --host 127.0.0.1 --port 8765

test:
	PYTHONPATH=src uv run pytest
```

- [ ] **Step 9: Install root devDeps**

Run: `pnpm install`
Expected: installs `@biomejs/biome` and `concurrently`; creates `node_modules/` and `pnpm-lock.yaml`.

- [ ] **Step 10: Verify biome and root typecheck pass**

Run: `pnpm lint && pnpm typecheck`
Expected: biome runs (empty workspace → all green); typecheck is a no-op since no `tsconfig.json` extends base yet. Both exit 0.

- [ ] **Step 11: Verify backend dev starts**

Run: `make -C apps/backend dev` (background, then `curl -sS http://127.0.0.1:8765/healthz`)
Expected: `{"status":"ok"}`. Kill the background process after.

- [ ] **Step 12: Commit**

```bash
git add pnpm-workspace.yaml package.json .npmrc tsconfig.base.json biome.json .gitignore apps/backend/Makefile pnpm-lock.yaml
git commit -m "chore: pnpm workspace + root config"
```

---

## Phase 1 — Shared Packages

### Task 2: `@splashh/config` package

**Files:**
- Create: `packages/config/package.json`
- Create: `packages/config/tsconfig.lib.json`
- Create: `packages/config/tsconfig.app.json`
- Create: `packages/config/vitest.config.ts`
- Create: `packages/config/index.ts`

- [ ] **Step 1: Create `packages/config/package.json`**

```json
{
  "name": "@splashh/config",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "main": "./index.ts",
  "exports": { ".": "./index.ts" },
  "scripts": {
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^5.6.0"
  }
}
```

- [ ] **Step 2: Create `packages/config/tsconfig.lib.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "composite": true,
    "declaration": true,
    "outDir": "dist",
    "rootDir": "."
  },
  "include": ["index.ts"]
}
```

- [ ] **Step 3: Create `packages/config/tsconfig.app.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "noEmit": true,
    "types": ["vite/client", "node"]
  }
}
```

- [ ] **Step 4: Create `packages/config/vitest.config.ts`**

```typescript
import { defineConfig } from "vitest/config";
export default defineConfig({
  test: {
    environment: "happy-dom",
    globals: true,
    coverage: { provider: "v8", reporter: ["text", "html"] },
  },
});
```

- [ ] **Step 5: Create `packages/config/index.ts`**

```typescript
export {};
// Re-export shared preset names so consumers can do:
//   import preset from "@splashh/config/vitest";
// in their vitest.config.ts (Vite resolves the .ts).
```

- [ ] **Step 6: Wire as workspace dep**

Add to the soon-to-be `apps/admin-pwa/package.json` and `apps/customer-pwa/package.json` (later tasks) as `"@splashh/config": "workspace:*"`. For now, run `pnpm install` to register the new package.

- [ ] **Step 7: Commit**

```bash
git add packages/config pnpm-lock.yaml
git commit -m "feat(packages): add @splashh/config"
```

### Task 3: `@splashh/ui` package — scaffold + brand theme

**Files:**
- Create: `packages/ui/package.json`
- Create: `packages/ui/tsconfig.json`
- Create: `packages/ui/vite.config.ts`
- Create: `packages/ui/tailwind.config.ts`
- Create: `packages/ui/postcss.config.js`
- Create: `packages/ui/components.json`
- Create: `packages/ui/src/styles/globals.css`
- Create: `packages/ui/src/lib/cn.ts`
- Create: `packages/ui/src/tokens.ts`
- Create: `packages/ui/src/index.ts`
- Create: `packages/ui/src/components/ui/button.tsx` (shadcn)
- Create: `packages/ui/src/components/ui/card.tsx` (shadcn)
- Create: `packages/ui/test-setup.ts`

- [ ] **Step 1: Create `packages/ui/package.json`**

```json
{
  "name": "@splashh/ui",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "exports": { ".": "./src/index.ts", "./styles.css": "./src/styles/globals.css" },
  "scripts": {
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@radix-ui/react-slot": "^1.1.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "lucide-react": "^0.460.0",
    "react-day-picker": "^9.0.0",
    "tailwind-merge": "^2.5.0"
  },
  "peerDependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@splashh/config": "workspace:*",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.20",
    "happy-dom": "^15.0.0",
    "postcss": "^8.4.49",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "tailwindcss": "^3.4.0",
    "tailwindcss-animate": "^1.0.7",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create `packages/ui/tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src", "test-setup.ts"]
}
```

- [ ] **Step 3: Create `packages/ui/vite.config.ts`**

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: ["./test-setup.ts"],
    coverage: { provider: "v8", reporter: ["text", "html"], thresholds: { lines: 80, functions: 80, branches: 70, statements: 80 } },
  },
});
```

- [ ] **Step 4: Create `packages/ui/tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

export default {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1rem", screens: { "2xl": "1280px" } },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)" },
    },
  },
  plugins: [animate],
} satisfies Config;
```

- [ ] **Step 5: Create `packages/ui/postcss.config.js`**

```javascript
export default { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

- [ ] **Step 6: Create `packages/ui/components.json`**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": { "config": "tailwind.config.ts", "css": "src/styles/globals.css", "baseColor": "slate", "cssVariables": true, "prefix": "" },
  "aliases": { "components": "@/components", "utils": "@/lib/cn", "ui": "@/components/ui", "lib": "@/lib", "hooks": "@/hooks" }
}
```

- [ ] **Step 7: Create `packages/ui/src/styles/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222 47% 11%;
    --card: 0 0% 100%;
    --card-foreground: 222 47% 11%;
    --primary: 199 89% 48%;            /* #0EA5E9 sky-500 */
    --primary-foreground: 0 0% 100%;
    --secondary: 210 40% 96%;
    --secondary-foreground: 222 47% 11%;
    --muted: 210 40% 96%;
    --muted-foreground: 215 16% 47%;
    --accent: 199 89% 48%;
    --accent-foreground: 0 0% 100%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;
    --border: 214 32% 91%;
    --input: 214 32% 91%;
    --ring: 199 89% 48%;
    --radius: 0.5rem;
  }
  .dark {
    --background: 222 47% 7%;
    --foreground: 210 40% 98%;
    --card: 222 47% 9%;
    --card-foreground: 210 40% 98%;
    --primary: 199 89% 60%;            /* #38BDF8 sky-400 */
    --primary-foreground: 222 47% 7%;
    --secondary: 217 33% 17%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 65%;
    --accent: 199 89% 60%;
    --accent-foreground: 222 47% 7%;
    --destructive: 0 63% 31%;
    --destructive-foreground: 210 40% 98%;
    --border: 217 33% 20%;
    --input: 217 33% 20%;
    --ring: 199 89% 60%;
  }
  * { @apply border-border; }
  body { @apply bg-background text-foreground; }
}
```

- [ ] **Step 8: Create `packages/ui/src/lib/cn.ts`**

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 9: Create `packages/ui/src/tokens.ts`**

```typescript
export const brand = {
  primary: { light: "#0EA5E9", dark: "#38BDF8" },
  name: "Splashh",
  tagline: "Book your club in seconds",
} as const;
```

- [ ] **Step 10: Create `packages/ui/src/components/ui/button.tsx`**

```typescript
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { buttonVariants };
```

- [ ] **Step 11: Create `packages/ui/src/components/ui/card.tsx`**

```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)} {...props} />
  ),
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />,
);
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-2xl font-semibold leading-none tracking-tight", className)} {...props} />
  ),
);
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => <p ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />,
);
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />,
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />,
);
CardFooter.displayName = "CardFooter";
```

- [ ] **Step 12: Create `packages/ui/src/index.ts`**

```typescript
export * from "./components/ui/button";
export * from "./components/ui/card";
export * from "./lib/cn";
export { brand } from "./tokens";
```

- [ ] **Step 13: Create `packages/ui/test-setup.ts`**

```typescript
import "@testing-library/jest-dom/vitest";
```

Add `@testing-library/jest-dom` and `@testing-library/react` to devDeps if not present (will be added when first component test is written in a later task). Skip if not needed yet.

- [ ] **Step 14: Install and verify**

Run: `pnpm install && pnpm --filter @splashh/ui typecheck`
Expected: installs succeed; typecheck exits 0.

- [ ] **Step 15: Commit**

```bash
git add packages/ui pnpm-lock.yaml
git commit -m "feat(packages/ui): scaffold with brand theme + Button/Card"
```

### Task 4: `@splashh/ui` — add more primitives via shadcn

**Files:**
- Create: `packages/ui/src/components/ui/input.tsx`
- Create: `packages/ui/src/components/ui/label.tsx`
- Create: `packages/ui/src/components/forms/form-field.tsx`
- Create: `packages/ui/test/button.test.tsx`
- Modify: `packages/ui/src/index.ts`

- [ ] **Step 1: Write failing test for Button**

Create `packages/ui/test/button.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
  });
  it("applies variant classes", () => {
    render(<Button variant="destructive">Delete</Button>);
    expect(screen.getByRole("button")).toHaveClass("bg-destructive");
  });
});
```

- [ ] **Step 2: Run test, verify pass**

Run: `pnpm --filter @splashh/ui test`
Expected: 2 passed (Button already implements this; the test pins the contract).

- [ ] **Step 3: Add Input primitive**

Create `packages/ui/src/components/ui/input.tsx`:

```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
```

- [ ] **Step 4: Add Label primitive**

Create `packages/ui/src/components/ui/label.tsx`:

```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export const Label = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    <label ref={ref} className={cn("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70", className)} {...props} />
  ),
);
Label.displayName = "Label";
```

- [ ] **Step 5: Add FormField composite**

Create `packages/ui/src/components/forms/form-field.tsx`:

```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface FormFieldProps {
  label: string;
  error?: string | null;
  description?: string;
  htmlFor?: string;
  children: React.ReactNode;
  className?: string;
}

export function FormField({ label, error, description, htmlFor, children, className }: FormFieldProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <label htmlFor={htmlFor} className="text-sm font-medium leading-none">
        {label}
      </label>
      {children}
      {description && !error && <p className="text-xs text-muted-foreground">{description}</p>}
      {error && (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Update `packages/ui/src/index.ts`**

```typescript
export * from "./components/ui/button";
export * from "./components/ui/card";
export * from "./components/ui/input";
export * from "./components/ui/label";
export * from "./components/forms/form-field";
export * from "./lib/cn";
export { brand } from "./tokens";
```

- [ ] **Step 7: Verify typecheck + tests pass**

Run: `pnpm --filter @splashh/ui typecheck && pnpm --filter @splashh/ui test`
Expected: both green.

- [ ] **Step 8: Commit**

```bash
git add packages/ui
git commit -m "feat(packages/ui): add Input/Label/FormField + Button test"
```

### Task 5: `@splashh/api-client` — scaffold + axios + auth store

**Files:**
- Create: `packages/api-client/package.json`
- Create: `packages/api-client/tsconfig.json`
- Create: `packages/api-client/vite.config.ts`
- Create: `packages/api-client/test-setup.ts`
- Create: `packages/api-client/src/api/client.ts`
- Create: `packages/api-client/src/auth/store.ts`
- Create: `packages/api-client/src/index.ts`
- Create: `packages/api-client/test/store.test.ts`

- [ ] **Step 1: Create `packages/api-client/package.json`**

```json
{
  "name": "@splashh/api-client",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "exports": { ".": "./src/index.ts" },
  "scripts": {
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "axios": "^1.7.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@splashh/config": "workspace:*",
    "@types/node": "^22.0.0",
    "happy-dom": "^15.0.0",
    "msw": "^2.6.0",
    "typescript": "^5.6.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create `packages/api-client/tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "types": ["node", "vitest/globals"]
  },
  "include": ["src", "test"]
}
```

- [ ] **Step 3: Create `packages/api-client/vite.config.ts`**

```typescript
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: ["./test-setup.ts"],
    coverage: { provider: "v8", reporter: ["text", "html"], thresholds: { lines: 80, functions: 80, branches: 70, statements: 80 } },
  },
});
```

- [ ] **Step 4: Create `packages/api-client/test-setup.ts`**

```typescript
// Vitest setup; extend later with MSW handlers.
```

- [ ] **Step 5: Write failing test for auth store**

Create `packages/api-client/test/store.test.ts`:

```typescript
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/auth/store";

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
  });
  it("starts unauthenticated", () => {
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
  it("setSession populates token + user", () => {
    useAuthStore.getState().setSession({
      accessToken: "abc",
      userId: "u1",
      tenantId: "t1",
      roles: ["tenant_admin"],
    });
    expect(useAuthStore.getState().accessToken).toBe("abc");
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().roles).toEqual(["tenant_admin"]);
  });
  it("clear wipes state", () => {
    useAuthStore.getState().setSession({ accessToken: "abc", userId: "u1", tenantId: "t1", roles: [] });
    useAuthStore.getState().clear();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
```

- [ ] **Step 6: Run test, verify fail**

Run: `pnpm --filter @splashh/api-client test`
Expected: FAIL with "Cannot find module @/auth/store".

- [ ] **Step 7: Implement auth store**

Create `packages/api-client/src/auth/store.ts`:

```typescript
import { create } from "zustand";

export interface Session {
  accessToken: string;
  userId: string;
  tenantId: string;
  roles: string[];
}

interface AuthState {
  accessToken: string | null;
  userId: string | null;
  tenantId: string | null;
  roles: string[];
  isAuthenticated: boolean;
  setSession: (s: Session) => void;
  setAccessToken: (token: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  userId: null,
  tenantId: null,
  roles: [],
  isAuthenticated: false,
  setSession: (s) =>
    set({
      accessToken: s.accessToken,
      userId: s.userId,
      tenantId: s.tenantId,
      roles: s.roles,
      isAuthenticated: true,
    }),
  setAccessToken: (token) => set({ accessToken: token, isAuthenticated: true }),
  clear: () =>
    set({ accessToken: null, userId: null, tenantId: null, roles: [], isAuthenticated: false }),
}));
```

- [ ] **Step 8: Create axios client**

Create `packages/api-client/src/api/client.ts`:

```typescript
import axios, { type AxiosInstance } from "axios";
import { useAuthStore } from "@/auth/store";

const baseURL = "/v1";

export const api: AxiosInstance = axios.create({ baseURL, withCredentials: true });

// Request: attach Bearer if logged in
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});
```

The 401 silent-refresh interceptor is added in Task 6.

- [ ] **Step 9: Create `packages/api-client/src/index.ts`**

```typescript
export { api } from "./api/client";
export { useAuthStore, type Session } from "./auth/store";
```

- [ ] **Step 10: Run tests, verify pass**

Run: `pnpm --filter @splashh/api-client test`
Expected: 3 tests pass.

- [ ] **Step 11: Verify typecheck**

Run: `pnpm --filter @splashh/api-client typecheck`
Expected: exit 0.

- [ ] **Step 12: Commit**

```bash
git add packages/api-client pnpm-lock.yaml
git commit -m "feat(packages/api-client): scaffold + axios + auth store"
```

### Task 6: `@splashh/api-client` — silent refresh interceptor (TDD)

**Files:**
- Modify: `packages/api-client/src/api/client.ts`
- Create: `packages/api-client/src/api/refresh.ts`
- Create: `packages/api-client/test/refresh.test.ts`

- [ ] **Step 1: Write failing test**

Create `packages/api-client/test/refresh.test.ts`:

```typescript
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/auth/store";
import { silentRefresh } from "@/api/refresh";

describe("silentRefresh", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("stores the new access token on success", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: "new-tok" }), { status: 200 }),
    );
    const token = await silentRefresh();
    expect(token).toBe("new-tok");
    expect(useAuthStore.getState().accessToken).toBe("new-tok");
  });

  it("clears the store on failure", async () => {
    useAuthStore.getState().setAccessToken("old");
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("", { status: 401 }));
    await expect(silentRefresh()).rejects.toBeTruthy();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("is single-flight: concurrent calls share one request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ access_token: "shared" }), { status: 200 }),
    );
    const [a, b] = await Promise.all([silentRefresh(), silentRefresh()]);
    expect(a).toBe("shared");
    expect(b).toBe("shared");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run test, verify fail**

Run: `pnpm --filter @splashh/api-client test -- refresh`
Expected: FAIL — cannot import `silentRefresh`.

- [ ] **Step 3: Implement silent refresh**

Create `packages/api-client/src/api/refresh.ts`:

```typescript
import { useAuthStore } from "@/auth/store";

let inflight: Promise<string> | null = null;

export async function silentRefresh(): Promise<string> {
  if (inflight) return inflight;
  inflight = doRefresh().finally(() => {
    inflight = null;
  });
  return inflight;
}

async function doRefresh(): Promise<string> {
  const res = await fetch("/v1/auth/refresh", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    useAuthStore.getState().clear();
    throw new Error(`refresh failed: ${res.status}`);
  }
  const data = (await res.json()) as { access_token: string; user_id?: string; tenant_id?: string; roles?: string[] };
  useAuthStore.getState().setSession({
    accessToken: data.access_token,
    userId: data.user_id ?? useAuthStore.getState().userId ?? "",
    tenantId: data.tenant_id ?? useAuthStore.getState().tenantId ?? "",
    roles: data.roles ?? useAuthStore.getState().roles,
  });
  return data.access_token;
}
```

- [ ] **Step 4: Wire 401 interceptor into `client.ts`**

Modify `packages/api-client/src/api/client.ts` — replace its body with:

```typescript
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/auth/store";
import { silentRefresh } from "./refresh";

const baseURL = "/v1";

export const api: AxiosInstance = axios.create({ baseURL, withCredentials: true });

// Request: attach Bearer
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

// Response: silent refresh on 401
type RetryConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config as RetryConfig | undefined;
    const status = error.response?.status;
    if (status === 401 && original && !original._retried) {
      original._retried = true;
      try {
        const token = await silentRefresh();
        original.headers?.set("Authorization", `Bearer ${token}`);
        return api.request(original);
      } catch {
        // refresh failed; bubble the original 401
        useAuthStore.getState().clear();
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);
```

- [ ] **Step 5: Export from `index.ts`**

Modify `packages/api-client/src/index.ts`:

```typescript
export { api } from "./api/client";
export { silentRefresh } from "./api/refresh";
export { useAuthStore, type Session } from "./auth/store";
```

- [ ] **Step 6: Run tests, verify pass**

Run: `pnpm --filter @splashh/api-client test`
Expected: all 6 tests pass (3 store + 3 refresh).

- [ ] **Step 7: Commit**

```bash
git add packages/api-client
git commit -m "feat(packages/api-client): single-flight silent refresh"
```

### Task 7: `@splashh/api-client` — typed query keys

**Files:**
- Create: `packages/api-client/src/query/keys.ts`
- Create: `packages/api-client/src/query/client.ts`
- Modify: `packages/api-client/src/index.ts`

- [ ] **Step 1: Create query keys factory**

Create `packages/api-client/src/query/keys.ts`:

```typescript
export const queryKeys = {
  facilities: {
    all: ["facilities"] as const,
    list: (tenantId: string) => ["facilities", "list", tenantId] as const,
    detail: (id: string) => ["facilities", "detail", id] as const,
  },
  resources: {
    listByFacility: (facilityId: string) => ["resources", "by-facility", facilityId] as const,
  },
  availability: {
    listByResource: (resourceId: string) => ["availability", "by-resource", resourceId] as const,
  },
  bookings: {
    listByResource: (resourceId: string, fromIso: string, toIso: string) =>
      ["bookings", "by-resource", resourceId, fromIso, toIso] as const,
    listByCustomer: (customerId: string) => ["bookings", "by-customer", customerId] as const,
    detail: (id: string) => ["bookings", "detail", id] as const,
  },
  customers: {
    list: (tenantId: string) => ["customers", "list", tenantId] as const,
    detail: (id: string) => ["customers", "detail", id] as const,
  },
} as const;
```

- [ ] **Step 2: Create query client preset**

Create `packages/api-client/src/query/client.ts`:

```typescript
import { QueryClient } from "@tanstack/react-query";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}
```

- [ ] **Step 3: Add `@tanstack/react-query` as a dep**

Run: `pnpm --filter @splashh/api-client add @tanstack/react-query@^5.59.0`
Expected: dep added to `packages/api-client/package.json`.

- [ ] **Step 4: Export from `index.ts`**

Modify `packages/api-client/src/index.ts`:

```typescript
export { api } from "./api/client";
export { silentRefresh } from "./api/refresh";
export { useAuthStore, type Session } from "./auth/store";
export { queryKeys } from "./query/keys";
export { createQueryClient } from "./query/client";
```

- [ ] **Step 5: Verify typecheck**

Run: `pnpm --filter @splashh/api-client typecheck`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add packages/api-client pnpm-lock.yaml
git commit -m "feat(packages/api-client): query keys + query client preset"
```

---

## Phase 2 — Backend Cookie Addition

### Task 8: Backend settings — cookie config

**Files:**
- Modify: `apps/backend/src/common/infrastructure/settings.py`
- Modify: `apps/backend/.env.example` (or create if missing)

- [ ] **Step 1: Read current settings**

Run: `cat apps/backend/src/common/infrastructure/settings.py | head -80`

Locate the `Settings` class and the existing `jwt_*` fields.

- [ ] **Step 2: Add cookie settings**

Add these fields to the `Settings` class:

```python
auth_refresh_cookie_name: str = "refresh_token"
auth_refresh_cookie_secure: bool = True
auth_refresh_cookie_samesite: str = "lax"
auth_refresh_cookie_path: str = "/v1/auth"
auth_refresh_cookie_max_age_seconds: int = 2_592_000  # 30 days
```

- [ ] **Step 3: Add settings env overrides in `.env.example`**

Create or append to `apps/backend/.env.example`:

```
AUTH_REFRESH_COOKIE_NAME=refresh_token
AUTH_REFRESH_COOKIE_SECURE=false
AUTH_REFRESH_COOKIE_SAMESITE=lax
AUTH_REFRESH_COOKIE_PATH=/v1/auth
AUTH_REFRESH_COOKIE_MAX_AGE_SECONDS=2592000
```

(`AUTH_REFRESH_COOKIE_SECURE=false` in dev so cookies work over http://127.0.0.1:8765.)

- [ ] **Step 4: Verify typecheck + tests still pass**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest -x --tb=short -q`
Expected: 48 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/backend
git commit -m "feat(backend): refresh-cookie settings"
```

### Task 9: Backend — login sets refresh cookie (TDD)

**Files:**
- Modify: `apps/backend/src/auth/interfaces/http/router.py`
- Modify: `apps/backend/tests/api/test_auth_endpoints.py`
- Modify: `apps/backend/src/auth/application/auth_service.py` (if needed for the `LoginResult`)

- [ ] **Step 1: Read current login handler and API test**

Read `apps/backend/src/auth/interfaces/http/router.py` and the `test_login_success` test in `apps/backend/tests/api/test_auth_endpoints.py`. Note the response shape (already a JSON body returning `access_token`, `refresh_token`, etc.).

- [ ] **Step 2: Write failing test**

Add to `apps/backend/tests/api/test_auth_endpoints.py`:

```python
async def test_login_sets_refresh_cookie(client):
    # Use an existing test tenant fixture, or create one
    # (mirror the pattern from test_login_success).
    resp = await client.post("/v1/auth/login", json={"email": "...", "password": "..."})
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie
    assert "Path=/v1/auth" in set_cookie
```

Use the same email/password the existing `test_login_success` uses. If fixtures are not already set up, follow the pattern from that test.

- [ ] **Step 3: Run test, verify fail**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest tests/api/test_auth_endpoints.py::test_login_sets_refresh_cookie -v`
Expected: FAIL — `set-cookie` header missing or doesn't contain `refresh_token=`.

- [ ] **Step 4: Implement cookie set on login**

In `apps/backend/src/auth/interfaces/http/router.py`, modify the `/login` handler to set the cookie. Read settings via `request.app.state.settings` (already populated by app factory) or via `Depends(get_settings)`:

```python
from fastapi import Request
from common.infrastructure.settings import get_settings

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    svc: AuthService = Depends(_auth_service),
) -> TokenResponse:
    result = await svc.login(email=payload.email, password=payload.password)
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=result.refresh_token,
        max_age=settings.auth_refresh_cookie_max_age_seconds,
        path=settings.auth_refresh_cookie_path,
        secure=settings.auth_refresh_cookie_secure,
        httponly=True,
        samesite=settings.auth_refresh_cookie_samesite,
    )
    return _to_token_response(result)
```

The `LoginResult` already has `refresh_token`. Note: in dev, `auth_refresh_cookie_secure=False` so the cookie sets over http.

- [ ] **Step 5: Run test, verify pass**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest tests/api/test_auth_endpoints.py::test_login_sets_refresh_cookie -v`
Expected: PASS.

- [ ] **Step 6: Run full suite**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest -q`
Expected: 49 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/backend
git commit -m "feat(backend): login sets httpOnly refresh cookie"
```

### Task 10: Backend — refresh reads cookie, sets new one on rotate, clears on reuse

**Files:**
- Modify: `apps/backend/src/auth/interfaces/http/router.py`
- Modify: `apps/backend/src/auth/application/auth_service.py` (add `refresh_via_cookie` helper or extend `refresh`)
- Modify: `apps/backend/tests/api/test_auth_endpoints.py`

- [ ] **Step 1: Write failing tests**

Add three tests to `apps/backend/tests/api/test_auth_endpoints.py`:

```python
async def test_refresh_via_cookie(client, login_response):
    # login first, capture the cookie
    cookies = login_response.cookies
    resp = await client.post("/v1/auth/refresh", cookies=cookies)  # no body
    assert resp.status_code == 200
    assert "refresh_token=" in resp.headers.get("set-cookie", "")

async def test_refresh_via_body_still_works(client, login_response):
    body = {"refresh_token": login_response.json()["refresh_token"]}
    resp = await client.post("/v1/auth/refresh", json=body)
    assert resp.status_code == 200

async def test_logout_clears_cookie(client, login_response):
    cookies = login_response.cookies
    resp = await client.post("/v1/auth/logout", cookies=cookies)
    assert resp.status_code == 204
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()
```

- [ ] **Step 2: Run tests, verify fail**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest -k "refresh_via_cookie or refresh_via_body or logout_clears" -v`
Expected: all three FAIL (cookie not consumed / not cleared).

- [ ] **Step 3: Update `/v1/auth/refresh` to read cookie first**

In `apps/backend/src/auth/interfaces/http/router.py`, modify the `refresh` handler:

```python
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    svc: AuthService = Depends(_auth_service),
) -> TokenResponse:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.auth_refresh_cookie_name)
    body_token = payload.refresh_token if payload else None
    token = cookie_token or body_token
    if not token:
        raise HTTPException(status_code=422, detail="Missing refresh token")
    result = await svc.refresh(refresh_token=token)
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=result.refresh_token,
        max_age=settings.auth_refresh_cookie_max_age_seconds,
        path=settings.auth_refresh_cookie_path,
        secure=settings.auth_refresh_cookie_secure,
        httponly=True,
        samesite=settings.auth_refresh_cookie_samesite,
    )
    return _to_token_response(result)
```

Make `RefreshRequest` optional: change the handler signature to accept `payload: RefreshRequest | None = Body(default=None)`. (Use `Body` from FastAPI.)

- [ ] **Step 4: Update `/v1/auth/logout` to clear cookie**

```python
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    payload: LogoutRequest | None = None,
    svc: AuthService = Depends(_auth_service),
) -> None:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.auth_refresh_cookie_name)
    body_token = payload.refresh_token if payload else None
    token = cookie_token or body_token
    if token:
        await svc.logout(refresh_token=token)
    # Always clear the cookie, even on invalid token (idempotent)
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=settings.auth_refresh_cookie_path,
    )
    return None
```

- [ ] **Step 5: Update `auth_service.refresh` to clear cookie on reuse detection**

In `apps/backend/src/auth/application/auth_service.py`, in the `refresh()` method, after the two `revoke_family` paths and before raising, the existing code already commits. The cookie clear happens in the router (which is fine — the router always calls `response.delete_cookie` on the failure path because the 401 response is generated by the global error handler).

But: a 401 from `auth_service.refresh` flows through FastAPI's exception handler, which produces a JSON error response. The `response` object in the router is not the same as the 401 response. So we need a different approach: a small FastAPI exception handler that clears the cookie on auth errors. Add to `apps/backend/src/common/interfaces/http/errors.py` (or wherever `register_error_handlers` lives):

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from common.domain.exceptions import Unauthorized
from common.infrastructure.settings import get_settings

@router_or_app.exception_handler(Unauthorized)
async def _unauthorized_handler(request: Request, exc: Unauthorized):
    settings = get_settings()
    response = JSONResponse(
        status_code=401,
        content={"type": "https://errors.splashh.dev/unauthorized", "title": "Unauthorized", "status": 401, "code": "unauthorized", "detail": str(exc)},
    )
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=settings.auth_refresh_cookie_path,
    )
    return response
```

If the existing error-handler module is more elaborate, integrate this handler there instead — match the existing pattern. The exact placement is in the module that defines `register_error_handlers(app)`.

- [ ] **Step 6: Run new tests, verify pass**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest -k "refresh_via_cookie or refresh_via_body or logout_clears" -v`
Expected: all 3 PASS.

- [ ] **Step 7: Run full suite**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest -q`
Expected: 52 passed.

- [ ] **Step 8: Smoke test live**

In a separate terminal:
```bash
cd apps/backend && PYTHONPATH=src ENVIRONMENT=development \
  JWT_ALGORITHM=HS256 JWT_SECRET="dev-only-jwt-secret-change-me-in-prod-please-32chars" \
  uv run uvicorn common.interfaces.http.app:create_app --factory --host 127.0.0.1 --port 8765
```

Then:
```bash
curl -i -sS -X POST http://127.0.0.1:8765/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@splashh-demo.example.com","password":"CorrectHorseBatteryStaple!9"}' \
  | head -20
```

Expected: response has `Set-Cookie: refresh_token=...; HttpOnly; ...; Path=/v1/auth; ...`.

```bash
curl -i -sS -X POST http://127.0.0.1:8765/v1/auth/refresh \
  -H "Cookie: refresh_token=<token>" | head -10
```

Expected: 200 with new `access_token` in body and rotated `Set-Cookie`.

- [ ] **Step 9: Commit**

```bash
git add apps/backend
git commit -m "feat(backend): refresh reads cookie, rotates, clears on reuse"
```

### Task 11: Backend — shorten access token TTL to 5 min

**Files:**
- Modify: `apps/backend/src/common/infrastructure/settings.py`

- [ ] **Step 1: Update TTL**

In `apps/backend/src/common/infrastructure/settings.py`, change:

```python
jwt_access_token_ttl_seconds: int = 300  # 5 min (was 15)
```

- [ ] **Step 2: Update any test that asserts on the exact TTL**

Run: `grep -rn "900\|expires_in=900\|expires_in == 900" apps/backend/tests/`

If any test hardcodes `900`, update to use `300` (or read from settings). Common locations: tests that decode tokens and check `exp - iat`.

- [ ] **Step 3: Run full suite**

Run: `cd apps/backend && PYTHONPATH=src uv run pytest -q`
Expected: 52 passed (or whatever the new count is).

- [ ] **Step 4: Commit**

```bash
git add apps/backend
git commit -m "feat(backend): shorten access token TTL to 5 min"
```

---

## Phase 3 — customer-pwa

### Task 12: customer-pwa Vite scaffold

**Files:**
- Create: `apps/customer-pwa/package.json`
- Create: `apps/customer-pwa/vite.config.ts`
- Create: `apps/customer-pwa/tsconfig.json`
- Create: `apps/customer-pwa/tsconfig.node.json`
- Create: `apps/customer-pwa/index.html`
- Create: `apps/customer-pwa/postcss.config.js`
- Create: `apps/customer-pwa/tailwind.config.ts`
- Create: `apps/customer-pwa/.env.development`
- Create: `apps/customer-pwa/src/main.tsx`
- Create: `apps/customer-pwa/src/App.tsx`
- Create: `apps/customer-pwa/src/styles/globals.css`

- [ ] **Step 1: Create `apps/customer-pwa/package.json`**

```json
{
  "name": "customer-pwa",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --port 5174 --strictPort",
    "build": "tsc -b && vite build",
    "preview": "vite preview --port 5174 --strictPort",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "@splashh/api-client": "workspace:*",
    "@splashh/ui": "workspace:*",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.0",
    "next-themes": "^0.4.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-hook-form": "^7.53.0",
    "react-router-dom": "^6.27.0",
    "zod": "^3.23.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@splashh/config": "workspace:*",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.20",
    "happy-dom": "^15.0.0",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "vite-plugin-pwa": "^0.20.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create `apps/customer-pwa/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "node:path";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "Splashh Sports",
        short_name: "Splashh",
        description: "Book your club in seconds",
        theme_color: "#0EA5E9",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
        shortcuts: [
          { name: "My Bookings", url: "/bookings", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
          { name: "Book a Court", url: "/facilities", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,woff2}"],
        runtimeCaching: [
          { urlPattern: /^\/v1\//, handler: "NetworkFirst", options: { cacheName: "api-cache", networkTimeoutSeconds: 10, expiration: { maxEntries: 100, maxAgeSeconds: 86400 }, cacheableResponse: { statuses: [0, 200] } } },
          { urlPattern: /\.(?:png|jpg|jpeg|svg|webp|avif|gif)$/, handler: "CacheFirst", options: { cacheName: "image-cache", expiration: { maxEntries: 200, maxAgeSeconds: 2592000 } } },
        ],
      },
    }),
  ],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      "/v1": { target: "http://127.0.0.1:8765", changeOrigin: false },
    },
  },
});
```

- [ ] **Step 3: Create `apps/customer-pwa/tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "types": ["vite/client", "vite-plugin-pwa/client"],
    "noEmit": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create `apps/customer-pwa/tsconfig.node.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "noEmit": true,
    "types": ["node"]
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Create `apps/customer-pwa/index.html`**

```html
<!doctype html>
<html lang="en" class="">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#0EA5E9" />
    <title>Splashh Sports</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create `apps/customer-pwa/postcss.config.js`**

```javascript
export default { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

- [ ] **Step 7: Create `apps/customer-pwa/tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  presets: [], // brand tokens come from @splashh/ui via globals.css; no duplication
  theme: { extend: {} },
} satisfies Config;
```

- [ ] **Step 8: Create `apps/customer-pwa/src/styles/globals.css`**

```css
@import "@splashh/ui/styles.css";
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }
```

- [ ] **Step 9: Create `apps/customer-pwa/src/main.tsx`**

```typescript
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import React from "react";
import ReactDOM from "react-dom/client";
import { createQueryClient } from "@splashh/api-client";
import App from "./App";
import "./styles/globals.css";

const queryClient = createQueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
```

- [ ] **Step 10: Create `apps/customer-pwa/src/App.tsx`**

```typescript
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./routes";

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  );
}
```

(`./routes` is created in Task 13.)

- [ ] **Step 11: Create `.env.development`**

```
VITE_APP_NAME=Splashh Sports
```

- [ ] **Step 12: Install + verify typecheck**

Run: `pnpm install && pnpm --filter customer-pwa typecheck`
Expected: typecheck fails because `./routes` doesn't exist yet — that's expected; Task 13 creates it. (If you want a green typecheck here, stub `src/routes.tsx` exporting a default component.)

- [ ] **Step 13: Commit**

```bash
git add apps/customer-pwa pnpm-lock.yaml
git commit -m "feat(customer-pwa): Vite + PWA scaffold"
```

### Task 13: customer-pwa — routing, auth bootstrap, login page

**Files:**
- Create: `apps/customer-pwa/src/routes/index.tsx`
- Create: `apps/customer-pwa/src/routes/protected.tsx`
- Create: `apps/customer-pwa/src/pages/LoginPage.tsx`
- Create: `apps/customer-pwa/src/features/auth/AuthBootstrap.tsx`
- Create: `apps/customer-pwa/src/features/auth/api.ts`
- Create: `apps/customer-pwa/src/features/auth/LoginForm.tsx`
- Create: `apps/customer-pwa/src/features/auth/useLogin.ts`
- Create: `apps/customer-pwa/src/pages/HomePage.tsx`
- Create: `apps/customer-pwa/test/login.test.tsx`

- [ ] **Step 1: Write failing LoginForm test**

Create `apps/customer-pwa/test/login.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginForm } from "@/features/auth/LoginForm";

const renderForm = () => {
  const qc = new QueryClient();
  const onSuccess = vi.fn();
  render(
    <QueryClientProvider client={qc}>
      <LoginForm onSuccess={onSuccess} />
    </QueryClientProvider>,
  );
  return { onSuccess };
};

describe("LoginForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows validation error for empty fields", async () => {
    const { onSuccess } = renderForm();
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("submits when fields are valid", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: "t" }), { status: 200 }),
    );
    const { onSuccess } = renderForm();
    await userEvent.type(screen.getByLabelText(/email/i), "u@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "password123");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });
});
```

Add `vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: { environment: "happy-dom", globals: true, setupFiles: ["./test-setup.ts"] },
});
```

Add `test-setup.ts`:
```typescript
import "@testing-library/jest-dom/vitest";
```

Add devDeps: `@testing-library/react`, `@testing-library/user-event`, `jsdom` (or stay with happy-dom).

- [ ] **Step 2: Run test, verify fail**

Run: `pnpm --filter customer-pwa test`
Expected: FAIL — `LoginForm` not found.

- [ ] **Step 3: Implement auth API wrapper**

Create `apps/customer-pwa/src/features/auth/api.ts`:

```typescript
import { api, useAuthStore } from "@splashh/api-client";

export async function loginRequest(email: string, password: string): Promise<void> {
  const res = await api.post("/auth/login", { email, password });
  const data = res.data as {
    access_token: string;
    user_id: string;
    tenant_id: string;
  };
  useAuthStore.getState().setSession({
    accessToken: data.access_token,
    userId: data.user_id,
    tenantId: data.tenant_id,
    roles: [], // populated by /me later; for now the JWT can be decoded if needed
  });
}
```

- [ ] **Step 4: Implement useLogin hook**

Create `apps/customer-pwa/src/features/auth/useLogin.ts`:

```typescript
import { useMutation } from "@tanstack/react-query";
import { loginRequest } from "./api";

export function useLogin() {
  return useMutation({
    mutationFn: (input: { email: string; password: string }) =>
      loginRequest(input.email, input.password),
  });
}
```

- [ ] **Step 5: Implement LoginForm**

Create `apps/customer-pwa/src/features/auth/LoginForm.tsx`:

```tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { Button, FormField, Input, Card, CardHeader, CardTitle, CardContent } from "@splashh/ui";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useLogin } from "./useLogin";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

export function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });
  const login = useLogin();

  const onSubmit = handleSubmit(async (data) => {
    try {
      await login.mutateAsync(data);
      onSuccess();
    } catch {
      // surface error via mutation state
    }
  });

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-xl">Log in</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <Input id="email" type="email" autoComplete="email" {...register("email")} />
          </FormField>
          <FormField label="Password" htmlFor="password" error={errors.password?.message}>
            <Input id="password" type="password" autoComplete="current-password" {...register("password")} />
          </FormField>
          {login.error && <p role="alert" className="text-sm text-destructive">{(login.error as Error).message ?? "Login failed"}</p>}
          <Button type="submit" disabled={isSubmitting || login.isPending} className="w-full">
            {login.isPending ? "Logging in…" : "Log in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

Add `@hookform/resolvers` to deps if not present: `pnpm --filter customer-pwa add @hookform/resolvers`.

- [ ] **Step 6: Implement AuthBootstrap**

Create `apps/customer-pwa/src/features/auth/AuthBootstrap.tsx`:

```tsx
import { silentRefresh } from "@splashh/api-client";
import { useEffect } from "react";
import { useAuthStore } from "@splashh/api-client";

export function AuthBootstrap({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!useAuthStore.getState().isAuthenticated) {
      silentRefresh().catch(() => {/* not logged in */});
    }
  }, []);
  return <>{children}</>;
}
```

- [ ] **Step 7: Implement LoginPage**

Create `apps/customer-pwa/src/pages/LoginPage.tsx`:

```tsx
import { LoginForm } from "@/features/auth/LoginForm";
import { useNavigate } from "react-router-dom";

export function LoginPage() {
  const navigate = useNavigate();
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <LoginForm onSuccess={() => navigate("/facilities", { replace: true })} />
    </main>
  );
}
```

- [ ] **Step 8: Implement HomePage placeholder**

Create `apps/customer-pwa/src/pages/HomePage.tsx`:

```tsx
import { Link } from "react-router-dom";
import { Button } from "@splashh/ui";

export function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="text-4xl font-bold">Splashh Sports</h1>
      <p className="text-muted-foreground">Book your club in seconds.</p>
      <Button asChild>
        <Link to="/login">Log in</Link>
      </Button>
    </main>
  );
}
```

- [ ] **Step 9: Implement protected route guard**

Create `apps/customer-pwa/src/routes/protected.tsx`:

```tsx
import { useAuthStore } from "@splashh/api-client";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export function ProtectedRoute() {
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();
  if (!isAuthed) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <Outlet />;
}
```

- [ ] **Step 10: Implement router**

Create `apps/customer-pwa/src/routes/index.tsx`:

```tsx
import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { AuthBootstrap } from "@/features/auth/AuthBootstrap";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { ProtectedRoute } from "./protected";

const FacilitiesPage = lazy(() => import("@/pages/FacilitiesPage").then((m) => ({ default: m.FacilitiesPage })));
const FacilityDetailPage = lazy(() => import("@/pages/FacilityDetailPage").then((m) => ({ default: m.FacilityDetailPage })));
const BookingsPage = lazy(() => import("@/pages/BookingsPage").then((m) => ({ default: m.BookingsPage })));

export function AppRouter() {
  return (
    <AuthBootstrap>
      <Suspense fallback={<div className="p-8 text-center text-muted-foreground">Loading…</div>}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/facilities" element={<FacilitiesPage />} />
            <Route path="/facilities/:id" element={<FacilityDetailPage />} />
            <Route path="/bookings" element={<BookingsPage />} />
          </Route>
          <Route path="*" element={<HomePage />} />
        </Routes>
      </Suspense>
    </AuthBootstrap>
  );
}
```

- [ ] **Step 11: Run tests, verify pass**

Run: `pnpm --filter customer-pwa test`
Expected: 2 passed (form tests). The router test isn't written yet — that's for a later task.

- [ ] **Step 12: Run typecheck**

Run: `pnpm --filter customer-pwa typecheck`
Expected: FAIL because `FacilitiesPage`, `FacilityDetailPage`, `BookingsPage` don't exist yet. Stub them with empty exports so typecheck passes:

Create each as:
```typescript
export function FacilitiesPage() { return <div>Facilities</div>; }
export function FacilityDetailPage() { return <div>Facility detail</div>; }
export function BookingsPage() { return <div>Bookings</div>; }
```

(Replace each in subsequent tasks.)

- [ ] **Step 13: Verify dev server starts**

Run: `pnpm --filter customer-pwa dev` (background, then `curl -sS http://127.0.0.1:5174/ | head -5`)
Expected: HTML response with `<div id="root">`. Kill background after.

- [ ] **Step 14: Commit**

```bash
git add apps/customer-pwa
git commit -m "feat(customer-pwa): auth bootstrap + login + routing skeleton"
```

### Task 14: customer-pwa — facilities list, detail, booking modal, my bookings

**Files:**
- Create: `apps/customer-pwa/src/features/facilities/api.ts`
- Create: `apps/customer-pwa/src/features/facilities/useFacilities.ts`
- Create: `apps/customer-pwa/src/features/facilities/useFacility.ts`
- Create: `apps/customer-pwa/src/pages/FacilitiesPage.tsx` (replace stub)
- Create: `apps/customer-pwa/src/pages/FacilityDetailPage.tsx` (replace stub)
- Create: `apps/customer-pwa/src/features/bookings/api.ts`
- Create: `apps/customer-pwa/src/features/bookings/useBookings.ts`
- Create: `apps/customer-pwa/src/features/bookings/useCreateBooking.ts`
- Create: `apps/customer-pwa/src/features/bookings/BookingDialog.tsx`
- Create: `apps/customer-pwa/src/pages/BookingsPage.tsx` (replace stub)
- Create: `apps/customer-pwa/test/booking.test.tsx`

- [ ] **Step 1: Write failing test for booking mutation**

Create `apps/customer-pwa/test/booking.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

import { api } from "@splashh/api-client";
import { useCreateBooking } from "@/features/bookings/useCreateBooking";

function Probe() {
  const create = useCreateBooking();
  return (
    <button
      onClick={() =>
        create.mutate({
          customer_id: "c1",
          resource_id: "r1",
          start_at: "2026-12-01T10:00:00Z",
          end_at: "2026-12-01T11:00:00Z",
          price_cents: 2500,
          currency: "AUD",
        })
      }
    >
      create
    </button>
  );
}

describe("useCreateBooking", () => {
  it("POSTs to /booking and returns the new booking", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { id: "b1", status: "confirmed" },
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <Probe />
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "create" }));
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/booking", expect.objectContaining({ resource_id: "r1" }));
    });
  });
});
```

- [ ] **Step 2: Run test, verify fail**

Run: `pnpm --filter customer-pwa test -- booking`
Expected: FAIL.

- [ ] **Step 3: Implement booking API + hooks**

Create `apps/customer-pwa/src/features/bookings/api.ts`:

```typescript
import { api } from "@splashh/api-client";

export interface BookingInput {
  customer_id: string;
  resource_id: string;
  start_at: string;
  end_at: string;
  price_cents: number;
  currency: string;
  notes?: string;
}
export interface Booking {
  id: string;
  customer_id: string;
  resource_id: string;
  start_at: string;
  end_at: string;
  status: "confirmed" | "cancelled" | "checked_in" | "completed" | "no_show";
  price_cents: number;
  currency: string;
  notes?: string | null;
  cancellation_reason?: string | null;
  cancelled_at?: string | null;
  checked_in_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export const bookingsApi = {
  create: (input: BookingInput) => api.post<Booking>("/booking", input).then((r) => r.data),
  listByResource: (resourceId: string, fromIso: string, toIso: string) =>
    api.get<{ data: Booking[] }>(`/booking/by-resource/${resourceId}`, { params: { from_at: fromIso, to_at: toIso } }).then((r) => r.data.data),
  listByCustomer: (customerId: string) =>
    api.get<{ data: Booking[] }>(`/booking/by-customer/${customerId}`).then((r) => r.data.data),
  get: (id: string) => api.get<Booking>(`/booking/${id}`).then((r) => r.data),
  cancel: (id: string, reason: string) => api.post<Booking>(`/booking/${id}/cancel`, { reason }).then((r) => r.data),
};
```

Create `apps/customer-pwa/src/features/bookings/useCreateBooking.ts`:

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { bookingsApi, type BookingInput } from "./api";
import { queryKeys } from "@splashh/api-client";

export function useCreateBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: BookingInput) => bookingsApi.create(input),
    onSettled: (_data, _err, vars) => {
      qc.invalidateQueries({ queryKey: ["bookings", "by-resource", vars.resource_id] });
    },
  });
}
```

Create `apps/customer-pwa/src/features/bookings/useBookings.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@splashh/api-client";
import { bookingsApi } from "./api";

export function useBookingsByCustomer(customerId: string | null) {
  return useQuery({
    queryKey: customerId ? queryKeys.bookings.listByCustomer(customerId) : ["bookings", "by-customer", "none"],
    queryFn: () => bookingsApi.listByCustomer(customerId!),
    enabled: !!customerId,
  });
}
```

- [ ] **Step 4: Implement facilities API + hooks**

Create `apps/customer-pwa/src/features/facilities/api.ts`:

```typescript
import { api } from "@splashh/api-client";

export interface Facility {
  id: string;
  name: string;
  slug: string;
  address_line1: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  timezone: string;
  status: string;
}
export interface Resource {
  id: string;
  facility_id: string;
  name: string;
  slug: string;
  resource_type: string;
  capacity: number;
  attributes: Record<string, unknown> | null;
  status: string;
}

export const facilitiesApi = {
  list: () => api.get<{ data: Facility[] }>("/facility").then((r) => r.data.data),
  get: (id: string) => api.get<Facility>(`/facility/${id}`).then((r) => r.data),
  listResources: (facilityId: string) =>
    api.get<{ data: Resource[] }>(`/facility/${facilityId}/resources`).then((r) => r.data.data),
};
```

Create `apps/customer-pwa/src/features/facilities/useFacilities.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@splashh/api-client";
import { facilitiesApi } from "./api";

export function useFacilities() {
  return useQuery({ queryKey: queryKeys.facilities.list("me"), queryFn: facilitiesApi.list });
}
export function useFacility(id: string | undefined) {
  return useQuery({
    queryKey: id ? queryKeys.facilities.detail(id) : ["facility", "none"],
    queryFn: () => facilitiesApi.get(id!),
    enabled: !!id,
  });
}
export function useResources(facilityId: string | undefined) {
  return useQuery({
    queryKey: facilityId ? queryKeys.resources.listByFacility(facilityId) : ["resources", "none"],
    queryFn: () => facilitiesApi.listResources(facilityId!),
    enabled: !!facilityId,
  });
}
```

- [ ] **Step 5: Run test, verify pass**

Run: `pnpm --filter customer-pwa test -- booking`
Expected: 1 passed.

- [ ] **Step 6: Implement FacilitiesPage**

Replace `apps/customer-pwa/src/pages/FacilitiesPage.tsx`:

```tsx
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@splashh/ui";
import { Link } from "react-router-dom";
import { useFacilities } from "@/features/facilities/useFacilities";

export function FacilitiesPage() {
  const { data, isLoading, error } = useFacilities();
  if (isLoading) return <div className="p-6">Loading…</div>;
  if (error) return <div className="p-6 text-destructive">Failed to load facilities.</div>;
  return (
    <main className="container py-6">
      <h1 className="mb-4 text-2xl font-semibold">Facilities</h1>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((f) => (
          <li key={f.id}>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">{f.name}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {f.city}, {f.state}
              </CardContent>
              <CardFooter>
                <Link to={`/facilities/${f.id}`} className="text-sm text-primary hover:underline">
                  View details →
                </Link>
              </CardFooter>
            </Card>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

- [ ] **Step 7: Implement FacilityDetailPage + BookingDialog**

Replace `apps/customer-pwa/src/pages/FacilityDetailPage.tsx`:

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";
import { useFacility, useResources } from "@/features/facilities/useFacilities";
import { BookingDialog } from "@/features/bookings/BookingDialog";

export function FacilityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const facility = useFacility(id);
  const resources = useResources(id);
  const [bookingResource, setBookingResource] = useState<string | null>(null);

  if (facility.isLoading) return <div className="p-6">Loading…</div>;
  if (facility.error) return <div className="p-6 text-destructive">Failed to load facility.</div>;
  const f = facility.data!;
  return (
    <main className="container py-6">
      <h1 className="text-2xl font-semibold">{f.name}</h1>
      <p className="text-sm text-muted-foreground">{f.address_line1}, {f.city} {f.state}</p>
      <h2 className="mt-6 text-lg font-medium">Resources</h2>
      <ul className="mt-2 grid gap-3 sm:grid-cols-2">
        {resources.data?.map((r) => (
          <li key={r.id}>
            <Card>
              <CardHeader><CardTitle className="text-base">{r.name}</CardTitle></CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Type: {r.resource_type} · Capacity: {r.capacity}
              </CardContent>
              <CardContent>
                <Button onClick={() => setBookingResource(r.id)}>Book</Button>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
      {bookingResource && (
        <BookingDialog
          resourceId={bookingResource}
          facilityId={f.id}
          onClose={() => setBookingResource(null)}
        />
      )}
    </main>
  );
}
```

Create `apps/customer-pwa/src/features/bookings/BookingDialog.tsx`:

```tsx
import { useState } from "react";
import { Button, FormField, Input } from "@splashh/ui";
import { useCreateBooking } from "./useCreateBooking";
import { useAuthStore } from "@splashh/api-client";

export function BookingDialog({ resourceId, facilityId, onClose }: { resourceId: string; facilityId: string; onClose: () => void }) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [price, setPrice] = useState(2500);
  const create = useCreateBooking();
  const customerId = useAuthStore((s) => s.userId);

  const onSubmit = async () => {
    if (!customerId) return;
    await create.mutateAsync({
      customer_id: customerId,
      resource_id: resourceId,
      start_at: new Date(start).toISOString(),
      end_at: new Date(end).toISOString(),
      price_cents: price,
      currency: "AUD",
    });
    onClose();
  };

  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg">
        <h2 className="text-lg font-semibold">Book resource</h2>
        <div className="mt-4 space-y-3">
          <FormField label="Start">
            <Input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
          </FormField>
          <FormField label="End">
            <Input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
          </FormField>
          <FormField label="Price (cents)">
            <Input type="number" min={0} value={price} onChange={(e) => setPrice(Number(e.target.value))} />
          </FormField>
          {create.error && <p role="alert" className="text-sm text-destructive">{(create.error as Error).message}</p>}
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={onSubmit} disabled={create.isPending}>
            {create.isPending ? "Booking…" : "Confirm booking"}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Implement BookingsPage**

Replace `apps/customer-pwa/src/pages/BookingsPage.tsx`:

```tsx
import { Button, Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";
import { useBookingsByCustomer } from "@/features/bookings/useBookings";
import { useAuthStore } from "@splashh/api-client";
import { bookingsApi } from "@/features/bookings/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@splashh/api-client";

function CancelButton({ id, onDone }: { id: string; onDone: () => void }) {
  const qc = useQueryClient();
  const cancel = useMutation({
    mutationFn: () => bookingsApi.cancel(id, "customer_request"),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["bookings"] });
      onDone();
    },
  });
  return (
    <Button size="sm" variant="destructive" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
      Cancel
    </Button>
  );
}

export function BookingsPage() {
  const userId = useAuthStore((s) => s.userId);
  const { data, isLoading, error } = useBookingsByCustomer(userId);
  if (isLoading) return <div className="p-6">Loading…</div>;
  if (error) return <div className="p-6 text-destructive">Failed to load bookings.</div>;
  return (
    <main className="container py-6">
      <h1 className="mb-4 text-2xl font-semibold">My bookings</h1>
      {data?.length === 0 && <p className="text-muted-foreground">No bookings yet.</p>}
      <ul className="space-y-3">
        {data?.map((b) => (
          <li key={b.id}>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{new Date(b.start_at).toLocaleString()}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Status: {b.status} · {b.price_cents / 100} {b.currency}
              </CardContent>
              <CardContent>
                {b.status === "confirmed" && <CancelButton id={b.id} onDone={() => {}} />}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

- [ ] **Step 9: Run typecheck + tests**

Run: `pnpm --filter customer-pwa typecheck && pnpm --filter customer-pwa test`
Expected: typecheck 0; tests 3 passed (login x2, booking x1).

- [ ] **Step 10: Live smoke (against running backend)**

In a terminal: `make -C apps/backend dev` (already running on 8765 from earlier sessions; if not, restart).

In another terminal:
```bash
pnpm --filter customer-pwa dev
```

Open http://127.0.0.1:5174/ in a browser. Manually:
1. Click "Log in", enter `admin@splashh-demo.example.com` / `CorrectHorseBatteryStaple!9`.
2. Verify redirect to `/facilities`.
3. Click a facility → click "Book" on a resource → fill in dates → Confirm.
4. Navigate to `/bookings` → see the new booking.
5. Click Cancel → status flips to `cancelled`.
6. DevTools → Application → Cookies → confirm `refresh_token` httpOnly cookie present.

- [ ] **Step 11: Commit**

```bash
git add apps/customer-pwa
git commit -m "feat(customer-pwa): facilities + booking flow + my bookings"
```

### Task 15: customer-pwa — install prompt + update banner

**Files:**
- Create: `apps/customer-pwa/src/components/PWAInstallPrompt.tsx`
- Create: `apps/customer-pwa/src/components/UpdateBanner.tsx`
- Modify: `apps/customer-pwa/src/App.tsx`

- [ ] **Step 1: Implement PWAInstallPrompt**

Create `apps/customer-pwa/src/components/PWAInstallPrompt.tsx`:

```tsx
import { Button, Card, CardContent, CardFooter, CardHeader, CardTitle } from "@splashh/ui";
import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISS_KEY = "pwa_install_dismissed_at";
const SHOW_AFTER_MS = 7 * 24 * 60 * 60 * 1000;
const SHOW_AFTER_VISITS = 3;

export function PWAInstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visits] = useState(() => Number(localStorage.getItem("pwa_visits") ?? "0"));

  useEffect(() => {
    const newCount = visits + 1;
    localStorage.setItem("pwa_visits", String(newCount));
    const dismissedAt = localStorage.getItem(DISMISS_KEY);
    if (dismissedAt && Date.now() - Number(dismissedAt) < SHOW_AFTER_MS) return;
    if (newCount < SHOW_AFTER_VISITS) return;
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, [visits]);

  if (!deferred) return null;

  const install = async () => {
    deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
  };
  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setDeferred(null);
  };

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 md:left-auto md:w-80">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Install Splashh</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Add to your home screen for the best experience.
        </CardContent>
        <CardFooter className="gap-2">
          <Button size="sm" onClick={install}>Install</Button>
          <Button size="sm" variant="ghost" onClick={dismiss}>Not now</Button>
        </CardFooter>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Implement UpdateBanner**

Create `apps/customer-pwa/src/components/UpdateBanner.tsx`:

```tsx
import { useRegisterSW } from "virtual:pwa-register/react";
import { Button } from "@splashh/ui";

export function UpdateBanner() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({ onRegisteredSW: () => {} });

  if (!needRefresh) return null;
  return (
    <div role="alert" className="fixed inset-x-0 top-0 z-50 border-b bg-card p-3 shadow">
      <div className="container flex items-center justify-between gap-3">
        <p className="text-sm">A new version of Splashh is available.</p>
        <Button
          size="sm"
          onClick={() => updateServiceWorker(true)}
        >
          Refresh
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Mount in App**

Modify `apps/customer-pwa/src/App.tsx`:

```tsx
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./routes";
import { PWAInstallPrompt } from "./components/PWAInstallPrompt";
import { UpdateBanner } from "./components/UpdateBanner";

export default function App() {
  return (
    <BrowserRouter>
      <UpdateBanner />
      <AppRouter />
      <PWAInstallPrompt />
    </BrowserRouter>
  );
}
```

- [ ] **Step 4: Verify build**

Run: `pnpm --filter customer-pwa build`
Expected: build succeeds; `dist/manifest.webmanifest` and `dist/sw.js` are produced.

- [ ] **Step 5: Commit**

```bash
git add apps/customer-pwa
git commit -m "feat(customer-pwa): install prompt + update banner"
```

---

## Phase 4 — admin-pwa

admin-pwa is structurally identical to customer-pwa. Reuse everything from `@splashh/ui` and `@splashh/api-client`. Tasks 16–21 mirror Tasks 12–15 with admin-specific routes, components, and the PWA manifest. The steps below are abbreviated; follow the customer-pwa pattern.

### Task 16: admin-pwa Vite scaffold

- [ ] **Step 1: Copy `apps/customer-pwa/package.json` to `apps/admin-pwa/package.json`**, change `name` to `admin-pwa`, change `--port 5174` to `--port 5173`, change dev script to `vite --port 5173 --strictPort`.
- [ ] **Step 2: Copy `vite.config.ts`** with port 5173 and `proxy /v1` → backend. Update manifest to `"Splashh Admin" / "Splashh Admin"`, theme_color same, shortcuts to "Today's Bookings" + "New Facility".
- [ ] **Step 3: Copy `tsconfig.json`, `tsconfig.node.json`, `index.html`** (title "Splashh Admin").
- [ ] **Step 4: Copy `postcss.config.js`, `tailwind.config.ts`, `src/styles/globals.css`**, `src/main.tsx`, `src/App.tsx`. Title in `index.html` becomes "Splashh Admin".
- [ ] **Step 5: Create `.env.development`**: `VITE_APP_NAME=Splashh Admin`.
- [ ] **Step 6: Stub `src/routes/index.tsx` and pages** (HomePage, LoginPage, AdminFacilitiesPage, AdminFacilityNewPage, AdminFacilityDetailPage, BookingsPage) as empty functional components so typecheck passes.
- [ ] **Step 7: `pnpm install && pnpm --filter admin-pwa typecheck`** — exit 0.
- [ ] **Step 8: Commit**: `feat(admin-pwa): Vite + PWA scaffold`.

### Task 17: admin-pwa — routing, auth bootstrap, login

- [ ] **Step 1: Copy LoginForm, AuthBootstrap, useLogin, api.ts, ProtectedRoute, RoleGate from customer-pwa verbatim.** Add a `<RoleGate roles={["tenant_admin"]}>` guard.
- [ ] **Step 2: Implement router** with: `/`, `/login`, `/admin/facilities` (read-only list), `/admin/facilities/new`, `/admin/facilities/:id`, `/bookings`, all under `<ProtectedRoute>` and admin ones under `<RoleGate>`.
- [ ] **Step 3: Tests** — copy login.test.tsx verbatim. Verify `pnpm --filter admin-pwa test` passes 2 tests.
- [ ] **Step 4: Commit**: `feat(admin-pwa): auth + routing skeleton`.

### Task 18: admin-pwa — facility list + new facility form

**Files:**
- Create: `apps/admin-pwa/src/features/admin/facilities/api.ts`
- Create: `apps/admin-pwa/src/features/admin/facilities/useAdminFacilities.ts`
- Create: `apps/admin-pwa/src/pages/AdminFacilitiesPage.tsx`
- Create: `apps/admin-pwa/src/pages/AdminFacilityNewPage.tsx`
- Create: `apps/admin-pwa/src/features/admin/facilities/NewFacilityForm.tsx`
- Create: `apps/admin-pwa/test/facility-create.test.tsx`

- [ ] **Step 1: Write failing test for create-facility mutation**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useCreateFacility } from "@/features/admin/facilities/useCreateFacility";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});
import { api } from "@splashh/api-client";

function Probe() {
  const create = useCreateFacility();
  return <button onClick={() => create.mutate({ name: "Court", slug: "court", city: "Sydney", state: "NSW", postal_code: "2000", country: "AU", timezone: "Australia/Sydney" } as any)}>create</button>;
}

it("posts to /facility", async () => {
  (api.post as any).mockResolvedValueOnce({ data: { id: "f1" } });
  render(<QueryClientProvider client={new QueryClient()}><Probe /></QueryClientProvider>);
  await userEvent.click(screen.getByRole("button", { name: "create" }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/facility", expect.objectContaining({ name: "Court" })));
});
```

- [ ] **Step 2: Run, verify fail.** Then implement `facilitiesApi.admin.create`, `useCreateFacility` (with invalidate), `AdminFacilitiesPage` (table view), `AdminFacilityNewPage` (form using RHF + Zod), `NewFacilityForm`.
- [ ] **Step 3: Run, verify pass.**
- [ ] **Step 4: Commit**: `feat(admin-pwa): facility list + create`.

### Task 19: admin-pwa — facility detail with tabs (resources + availability)

- [ ] **Step 1: Implement `AdminFacilityDetailPage`** with tabs: Info, Resources, Availability, Bookings.
- [ ] **Step 2: Implement resource create form** (RHF + Zod): name, slug, resource_type (enum), capacity, attributes (JSON text).
- [ ] **Step 3: Implement availability rule form**: day_of_week, start_time, end_time, slot_duration_minutes.
- [ ] **Step 4: Write tests** for both forms (validation + submit).
- [ ] **Step 5: Commit**: `feat(admin-pwa): facility detail with tabs`.

### Task 20: admin-pwa — bookings list (today's, checkin/complete)

- [ ] **Step 1: Implement `BookingsPage`** for admin: show all bookings for a chosen date (default: today), grouped by facility.
- [ ] **Step 2: Add CheckIn and Complete buttons** (POST `/booking/:id/check-in` and `/complete`).
- [ ] **Step 3: Test** the check-in mutation.
- [ ] **Step 4: Commit**: `feat(admin-pwa): bookings list with checkin/complete`.

### Task 21: admin-pwa — install prompt + update banner

- [ ] **Step 1: Copy PWAInstallPrompt and UpdateBanner from customer-pwa.**
- [ ] **Step 2: Mount in App.**
- [ ] **Step 3: Verify build** with `pnpm --filter admin-pwa build`.
- [ ] **Step 4: Commit**: `feat(admin-pwa): install prompt + update banner`.

---

## Phase 5 — E2E + Polish

### Task 22: Playwright config + admin-pwa smoke

**Files:**
- Create: `playwright.config.ts`
- Create: `e2e/admin.spec.ts`

- [ ] **Step 1: Install Playwright**

```bash
pnpm add -Dw @playwright/test @axe-core/playwright
pnpm exec playwright install --with-deps chromium
```

- [ ] **Step 2: Create `playwright.config.ts`**

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  projects: [
    { name: "admin", use: { ...devices["Desktop Chrome"], baseURL: "http://127.0.0.1:5173" } },
    { name: "customer", use: { ...devices["Desktop Chrome"], baseURL: "http://127.0.0.1:5174" } },
  ],
  webServer: [
    { command: "make -C apps/backend dev", url: "http://127.0.0.1:8765/healthz", reuseExistingServer: true, timeout: 30_000 },
    { command: "pnpm --filter admin-pwa dev", url: "http://127.0.0.1:5173", reuseExistingServer: true, timeout: 30_000 },
    { command: "pnpm --filter customer-pwa dev", url: "http://127.0.0.1:5174", reuseExistingServer: true, timeout: 30_000 },
  ],
});
```

- [ ] **Step 3: Create `e2e/admin.spec.ts`**

```typescript
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const SLUG = `e2e-admin-${Date.now()}`;

test("admin: register tenant, create facility, add resource", async ({ page }) => {
  await page.goto("/login");
  // Register a new tenant (admin-pwa exposes /register-tenant).
  await page.getByRole("link", { name: /create.*account/i }).click();
  await page.getByLabel("Tenant name").fill("E2E Admin");
  await page.getByLabel("Slug").fill(SLUG);
  await page.getByLabel("Contact email").fill(`contact-${SLUG}@example.com`);
  await page.getByLabel("Admin email").fill(`admin-${SLUG}@example.com`);
  await page.getByLabel("Password").fill("CorrectHorseBatteryStaple!9");
  await page.getByLabel("Admin name").fill("E2E");
  await page.getByRole("button", { name: /register/i }).click();
  // After register, app may auto-login and land on /admin/facilities.
  await page.goto("/admin/facilities/new");
  await page.getByLabel("Name").fill("E2E Court");
  await page.getByLabel("Slug").fill(`e2e-court-${SLUG}`);
  await page.getByLabel("City").fill("Sydney");
  await page.getByLabel("State").fill("NSW");
  await page.getByLabel("Postal code").fill("2000");
  await page.getByLabel("Country").fill("AU");
  await page.getByLabel("Timezone").fill("Australia/Sydney");
  await page.getByRole("button", { name: /create/i }).click();
  await expect(page.getByRole("heading", { name: "E2E Court" })).toBeVisible();

  // Accessibility scan
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((v) => v.impact === "critical" || v.impact === "serious")).toEqual([]);
});
```

- [ ] **Step 4: Run admin E2E**

Run: `pnpm test:e2e -- --project=admin`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add e2e playwright.config.ts package.json pnpm-lock.yaml
git commit -m "test(e2e): admin-pwa smoke + playwright config"
```

### Task 23: customer-pwa E2E smoke

**Files:**
- Create: `e2e/customer.spec.ts`

- [ ] **Step 1: Create `e2e/customer.spec.ts`** mirroring the admin flow: register a customer-pwa user (this app exposes register-tenant too), browse facilities, book a slot, see it in /bookings, cancel.
- [ ] **Step 2: Run**: `pnpm test:e2e -- --project=customer` — passes 1 spec.
- [ ] **Step 3: Commit**: `test(e2e): customer-pwa smoke`.

### Task 24: README + dev workflow docs

**Files:**
- Create: `apps/customer-pwa/README.md`
- Create: `apps/admin-pwa/README.md`
- Create: `packages/ui/README.md`
- Create: `packages/api-client/README.md`
- Modify: `README.md` (root)

- [ ] **Step 1: Each package README** documents: purpose, install, dev, build, test. Short — under 80 lines each.
- [ ] **Step 2: Root README** gets a new section: "Frontend PWAs" with: stack, repo layout, how to run `pnpm dev`, how to build, how to add a shadcn primitive.
- [ ] **Step 3: Commit**: `docs: frontend PWA READMEs`.

---

## Self-Review Checklist

- [ ] Every spec section (§3-§12) is covered by at least one task.
- [ ] No `TBD` / `TODO` / `fill in` strings remain in this plan.
- [ ] All function/method names referenced in later tasks exist in earlier tasks (`silentRefresh`, `useAuthStore`, `api`, `createQueryClient`, `queryKeys`).
- [ ] Type names match across tasks (`Session`, `Facility`, `Resource`, `Booking`, `BookingInput`).
- [ ] All `pnpm`/`uv` commands include the working directory prefix.
- [ ] Every task ends with `git commit` and a verification step.
