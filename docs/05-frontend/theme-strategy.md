# Theme Strategy

> Dark mode via class strategy. Tenant theming via CSS variables. Persisted preference. No FOUC.

This document establishes theming strategies for the Splashh Sports Platform. We support dark mode, light mode, and tenant-specific branding.

---

## Dark Mode (Class Strategy)

We use the **class** strategy for dark mode, which gives us explicit control over theming:

```typescript
// tailwind.config.ts
export default {
  darkMode: 'class',
};
```

### Theme Provider

```typescript
// lib/theme/ThemeProvider.tsx
import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'system';
    return (localStorage.getItem('theme') as Theme) || 'system';
  });

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const root = document.documentElement;

    const getSystemTheme = (): 'light' | 'dark' => {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    };

    const updateTheme = () => {
      const resolved = theme === 'system' ? getSystemTheme() : theme;
      setResolvedTheme(resolved);

      if (resolved === 'dark') {
        root.classList.add('dark');
        root.classList.remove('light');
      } else {
        root.classList.remove('dark');
        root.classList.add('light');
      }
    };

    updateTheme();

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (theme === 'system') {
        updateTheme();
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

---

## Preventing Flash of Unstyled Content (FOUC)

To prevent FOUC, we must apply the theme before React hydrates:

```typescript
// index.html - Inline script runs before React
<!DOCTYPE html>
<html lang="en">
  <head>
    <script>
      // Immediately apply theme to prevent FOUC
      (function() {
        const theme = localStorage.getItem('theme') || 'system';
        const root = document.documentElement;

        if (theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
          root.classList.add('dark');
        } else {
          root.classList.add('light');
        }
      })();
    </script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
```

---

## Theme Toggle Component

```typescript
// components/theme/ThemeToggle.tsx
import { useTheme } from '@/lib/theme/ThemeProvider';
import { Moon, Sun, Monitor } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu';

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          {resolvedTheme === 'dark' ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme('light')}>
          <Sun className="mr-2 h-4 w-4" />
          Light
          {theme === 'light' && <Check className="ml-auto h-4 w-4" />}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')}>
          <Moon className="mr-2 h-4 w-4" />
          Dark
          {theme === 'dark' && <Check className="ml-auto h-4 w-4" />}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('system')}>
          <Monitor className="mr-2 h-4 w-4" />
          System
          {theme === 'system' && <Check className="ml-auto h-4 w-4" />}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

---

## Tenant Theming

Tenants can customize colors via CSS variables:

```typescript
// lib/theme/tenant.ts
interface TenantTheme {
  id: string;
  name: string;
  colors: {
    primary: string;
    primaryForeground: string;
    secondary: string;
    secondaryForeground: string;
    accent: string;
    accentForeground: string;
  };
  logo?: string;
}

// Apply tenant theme
export function applyTenantTheme(tenant: TenantTheme) {
  const root = document.documentElement;

  root.style.setProperty('--color-primary', tenant.colors.primary);
  root.style.setProperty('--color-primary-foreground', tenant.colors.primaryForeground);
  root.style.setProperty('--color-secondary', tenant.colors.secondary);
  root.style.setProperty('--color-secondary-foreground', tenant.colors.secondaryForeground);
  root.style.setProperty('--color-accent', tenant.colors.accent);
  root.style.setProperty('--color-accent-foreground', tenant.colors.accentForeground);

  // Set data attribute for CSS selectors
  root.setAttribute('data-theme', tenant.id);
}

// CSS variables for tenant theming
:root {
  --color-primary: #2563eb;
  --color-primary-foreground: #ffffff;
  --color-secondary: #64748b;
  --color-secondary-foreground: #ffffff;
  --color-accent: #f1f5f9;
  --color-accent-foreground: #0f172a;
}
```

### Tenant Theme Hook

```typescript
// hooks/useTenantTheme.ts
import { useEffect } from 'react';
import { useTenant } from './useTenant';
import { applyTenantTheme } from '@/lib/theme/tenant';

export function useTenantTheme() {
  const { tenant } = useTenant();

  useEffect(() => {
    if (tenant) {
      applyTenantTheme(tenant);
    }
  }, [tenant]);

  return tenant;
}
```

---

## CSS Variables for All Themes

```css
/* styles/themes.css */

/* Light theme (default) */
:root,
:root[data-theme="light"] {
  --color-background: #ffffff;
  --color-foreground: #0f172a;

  --color-muted: #f1f5f9;
  --color-muted-foreground: #64748b;

  --color-card: #ffffff;
  --color-card-foreground: #0f172a;

  --color-popover: #ffffff;
  --color-popover-foreground: #0f172a;

  --color-border: #e2e8f0;
  --color-input: #e2e8f0;

  --color-ring: #2563eb;

  --radius: 0.5rem;
}

/* Dark theme */
:root.dark,
:root[data-theme="dark"] {
  --color-background: #0f172a;
  --color-foreground: #f8fafc;

  --color-muted: #1e293b;
  --color-muted-foreground: #94a3b8;

  --color-card: #1e293b;
  --color-card-foreground: #f8fafc;

  --color-popover: #1e293b;
  --color-popover-foreground: #f8fafc;

  --color-border: #334155;
  --color-input: #334155;

  --color-ring: #3b82f6;

  --radius: 0.5rem;
}

/* Tenant theming - overrides primary colors */
:root[data-theme="acme"] {
  --color-primary: #e11d48;
  --color-primary-foreground: #ffffff;
}

:root[data-theme="splashh"] {
  --color-primary: #0066cc;
  --color-primary-foreground: #ffffff;
}
```

---

## Using Theme Tokens in Components

```typescript
// Components automatically use theme tokens
function Card() {
  return (
    <div className="bg-card text-card-foreground rounded-lg border border-border p-6 shadow-sm">
      {/* All colors automatically respond to theme changes */}
      <h2 className="text-lg font-semibold">Card Title</h2>
      <p className="text-muted-foreground">Description text</p>
    </div>
  );
}
```

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| Class strategy | Explicit control, SSR friendly | Requires JS |
| System preference | Automatic dark mode | Less control |
| CSS variables | Runtime theming, tenant customization | Browser support |
| FOUC prevention | No flash | Inline script required |

---

## Related Documents

- [Design Tokens](design-tokens.md) — Token architecture
- [Tailwind Dark Mode](https://tailwindcss.com/docs/dark-mode) — Full reference
