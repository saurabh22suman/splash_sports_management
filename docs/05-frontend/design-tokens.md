# Design Tokens

> Three-layer tokens. Tailwind config maps to tokens. CSS custom properties for runtime theming. Token naming.

This document establishes the design token architecture for the Splashh Sports Platform. Design tokens are the visual design atoms of the design system — specifically, they are named entities that store visual design attributes.

---

## Three-Layer Token System

### 1. Primitive Tokens

Raw values (colors, spacing, typography) — not used directly in components:

```typescript
// tailwind.config.ts - Primitive tokens
export default {
  theme: {
    extend: {
      // Colors - primitive
      colors: {
        // Blues
        blue: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // Grays
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          // ... full scale
        },
      },

      // Spacing - primitive
      spacing: {
        '0': '0px',
        '0.5': '0.125rem',  // 2px
        '1': '0.25rem',     // 4px
        '1.5': '0.375rem',  // 6px
        '2': '0.5rem',      // 8px
        // ... up to 96 (24rem)
        '128': '32rem',
        '144': '36rem',
      },

      // Typography - primitive
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],     // 12px
        'sm': ['0.875rem', { lineHeight: '1.25rem' }], // 14px
        'base': ['1rem', { lineHeight: '1.5rem' }],    // 16px
        'lg': ['1.125rem', { lineHeight: '1.75rem' }], // 18px
        'xl': ['1.25rem', { lineHeight: '1.75rem' }], // 20px
        // ... up to 9xl
      },

      // Border radius - primitive
      borderRadius: {
        'none': '0px',
        'sm': '0.125rem',
        'DEFAULT': '0.25rem',
        'md': '0.375rem',
        'lg': '0.5rem',
        'xl': '0.75rem',
        '2xl': '1rem',
        'full': '9999px',
      },
    },
  },
};
```

### 2. Semantic Tokens

Abstract meanings tied to context:

```typescript
// tailwind.config.ts - Semantic tokens
export default {
  theme: {
    extend: {
      colors: {
        // Brand colors - semantic
        primary: {
          DEFAULT: '{colors.blue.600}',
          foreground: '#ffffff',
          50: '{colors.blue.50}',
          100: '{colors.blue.100}',
          200: '{colors.blue.200}',
          300: '{colors.blue.300}',
          400: '{colors.blue.400}',
          500: '{colors.blue.500}',
          600: '{colors.blue.600}',
          700: '{colors.blue.700}',
          800: '{colors.blue.800}',
          900: '{colors.blue.900}',
          950: '{colors.blue.950}',
        },

        // Functional colors - semantic
        success: {
          DEFAULT: '#22c55e',
          foreground: '#ffffff',
        },
        warning: {
          DEFAULT: '#f59e0b',
          foreground: '#000000',
        },
        destructive: {
          DEFAULT: '#ef4444',
          foreground: '#ffffff',
        },

        // Surface colors - semantic
        background: {
          DEFAULT: '#ffffff',
          foreground: '{colors.gray.900}',
        },
        foreground: {
          DEFAULT: '{colors.gray.900}',
          muted: '{colors.gray.500}',
        },
        muted: {
          DEFAULT: '{colors.gray.100}',
          foreground: '{colors.gray.500}',
        },
        card: {
          DEFAULT: '#ffffff',
          foreground: '{colors.gray.900}',
        },
        border: {
          DEFAULT: '{colors.gray.200}',
          foreground: '{colors.gray.900}',
        },
        input: {
          DEFAULT: '{colors.gray.200}',
          foreground: '{colors.gray.900}',
        },
        ring: {
          DEFAULT: '{colors.blue.600}',
        },
      },

      // Typography - semantic
      fontSize: {
        'heading-1': ['2.25rem', { lineHeight: '2.5rem', fontWeight: '700' }],
        'heading-2': ['1.875rem', { lineHeight: '2.25rem', fontWeight: '600' }],
        'heading-3': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
        'heading-4': ['1.25rem', { lineHeight: '1.75rem', fontWeight: '600' }],
        'body': ['1rem', { lineHeight: '1.5rem' }],
        'body-sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'caption': ['0.75rem', { lineHeight: '1rem' }],
      },

      // Spacing - semantic
      spacing: {
        'gutter': '1rem',        // Mobile gutter
        'gutter-md': '1.5rem',    // Tablet gutter
        'gutter-lg': '2rem',      // Desktop gutter
        'section': '4rem',        // Section spacing
        'card': '1.5rem',        // Card padding
      },

      // Border radius - semantic
      borderRadius: {
        'button': '0.375rem',
        'input': '0.375rem',
        'card': '0.5rem',
        'modal': '0.75rem',
      },
    },
  },
};
```

### 3. Component Tokens

Specific to components:

```typescript
// tailwind.config.ts - Component tokens
export default {
  theme: {
    extend: {
      // Button tokens
      button: {
        'height': {
          'sm': '2rem',
          'DEFAULT': '2.5rem',
          'lg': '3rem',
        },
        'padding': {
          'sm': '0.5rem 0.75rem',
          'DEFAULT': '0.75rem 1.5rem',
          'lg': '1rem 2rem',
        },
        'font-size': {
          'sm': '0.875rem',
          'DEFAULT': '1rem',
          'lg': '1.125rem',
        },
      },

      // Input tokens
      input: {
        'height': '2.5rem',
        'padding': '0.5rem 0.75rem',
      },

      // Card tokens
      card: {
        'padding': '1.5rem',
        'radius': '0.5rem',
        'shadow': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -2px rgb(0 0 0 / 0.1)',
      },
    },
  },
};
```

---

## CSS Custom Properties

For runtime theming support:

```css
/* styles/themes.css */
:root {
  /* Primitive - Colors */
  --color-blue-50: #eff6ff;
  --color-blue-100: #dbeafe;
  /* ... */

  /* Semantic - Brand */
  --color-primary: #2563eb;
  --color-primary-foreground: #ffffff;

  /* Semantic - Functional */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-destructive: #ef4444;

  /* Semantic - Surface */
  --color-background: #ffffff;
  --color-foreground: #0f172a;
  --color-muted: #f1f5f9;
  --color-muted-foreground: #64748b;
  --color-card: #ffffff;
  --color-card-foreground: #0f172a;
  --color-border: #e2e8f0;
  --color-input: #e2e8f0;
  --color-ring: #2563eb;

  /* Spacing */
  --spacing-gutter: 1rem;
  --spacing-section: 4rem;
  --spacing-card: 1.5rem;

  /* Typography */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;

  /* Border radius */
  --radius-button: 0.375rem;
  --radius-input: 0.375rem;
  --radius-card: 0.5rem;
}

/* Dark theme */
.dark {
  --color-background: #0f172a;
  --color-foreground: #f8fafc;
  --color-muted: #1e293b;
  --color-muted-foreground: #94a3b8;
  --color-card: #1e293b;
  --color-card-foreground: #f8fafc;
  --color-border: #334155;
  --color-input: #334155;
}

/* Tenant theming - apply via CSS variables on root */
[data-theme="splashh"] {
  --color-primary: #0066cc;
}

[data-theme="acme"] {
  --color-primary: #e11d48;
}
```

---

## Token Naming Conventions

| Category | Pattern | Example |
|----------|---------|---------|
| Primitive colors | `{color}-{shade}` | `blue-500`, `gray-100` |
| Semantic colors | `{role}` or `{role}-{state}` | `primary`, `destructive`, `success` |
| Surface colors | `{surface}-{property}` | `background`, `card-foreground` |
| Spacing | `{name}` | `gutter`, `section`, `card` |
| Typography | `{element}-{property}` | `heading-1`, `body-sm` |
| Border radius | `{element}` | `button`, `input`, `card` |

---

## Using Tokens in Components

```typescript
// components/ui/Button.tsx
export function Button({
  variant = 'default',
  size = 'default',
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        // Use semantic tokens
        'inline-flex items-center justify-center rounded-button font-medium',
        'transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'disabled:pointer-events-none disabled:opacity-50',

        // Variant tokens
        variant === 'default' && 'bg-primary text-primary-foreground hover:bg-primary/90',
        variant === 'destructive' && 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        variant === 'outline' && 'border border-input bg-background hover:bg-muted hover:text-muted-foreground',
        variant === 'secondary' && 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        variant === 'ghost' && 'hover:bg-muted hover:text-muted-foreground',
        variant === 'link' && 'text-primary underline-offset-4 hover:underline',

        // Size tokens
        size === 'sm' && 'h-9 px-3 text-sm',
        size === 'default' && 'h-10 px-4',
        size === 'lg' && 'h-11 px-8 text-lg',

        className
      )}
      {...props}
    />
  );
}
```

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| Three-layer tokens | Clear abstraction, easy theming | More config files |
| CSS variables | Runtime theming, dynamic changes | Slightly more complex build |
| Tailwind mapping | Type safety, IDE support | Learning curve |

---

## Related Documents

- [Theme Strategy](theme-strategy.md) — Dark mode and tenant theming
- [Component Design](component-design.md) — Token usage in components
- [Design Tokens W3C Draft](https://design-tokens.github.io/community-group/format/) — Full specification
