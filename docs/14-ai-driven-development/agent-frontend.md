# Frontend Agent

> Responsibilities, inputs, outputs, and collaboration rules for the Frontend Agent.

The Frontend Agent implements the client-side React PWA. It owns the **user interface** — ensuring it is accessible, responsive, and follows the design system.

---

## Responsibilities

The Backend Agent is responsible for:

1. **React PWA implementation** — Building components, pages, and routing
2. **Accessibility (a11y)** — Ensuring WCAG 2.2 AA compliance
3. **Responsive UI** — Supporting mobile, tablet, and desktop breakpoints
4. **Design system adherence** — Using design tokens and components consistently
5. **State management** — Implementing server state (TanStack Query) and client state
6. **Offline support** — Service worker, cache strategies, sync
7. **Component tests** — Writing tests for UI components
8. **Storybook stories** — Documenting components visually

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **API contract** | Architect Agent | OpenAPI spec for backend endpoints |
| **Design system** | [Design Tokens](../05-frontend/design-tokens.md) | Colors, typography, spacing |
| **Wireframes/mockups** | Product/Design | Visual expectations |
| **Story document** | Product Agent | User stories and acceptance criteria |
| **Frontend structure** | [Frontend docs](../05-frontend/) | Folder structure, patterns |

---

## Outputs

| Output | Description |
|---|---|
| **React components** | Components in `src/components/` |
| **Pages** | Route pages in `src/pages/` |
| **Hooks** | Custom hooks in `src/hooks/` |
| **API client** | Generated or typed API client |
| **Component tests** | Jest/Vitest tests |
| **Storybook stories** | Visual documentation |
| **i18n strings** | Translation keys |

### Code Structure Example

```
apps/customer-pwa/
├── src/
│   ├── components/
│   │   ├── membership/
│   │   │   ├── MembershipCard.tsx
│   │   │   ├── MembershipCard.stories.tsx
│   │   │   └── MembershipCard.test.tsx
│   │   └── ui/
│   ├── pages/
│   │   └── membership/
│   │       └── FreezePage.tsx
│   ├── hooks/
│   │   └── useMembership.ts
│   ├── api/
│   │   └── membership.ts
│   ├── i18n/
│   └── App.tsx
└── package.json
```

---

## Deliverables Checklist

Before requesting review, the Frontend Agent must confirm:

- [ ] All pages/components from design are implemented
- [ ] API contract is consumed correctly
- [ ] Accessibility: keyboard navigation works
- [ ] Accessibility: screen reader tested (axe-core)
- [ ] Responsive: all breakpoints work
- [ ] Offline: critical flows work without network
- [ ] No console errors
- [ ] Lint passes
- [ ] Type check passes
- [ ] Tests pass

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| Lint | 0 errors | `eslint` |
| Type check | 0 errors | `tsc --noEmit` |
| Unit test pass | >80% pass | `vitest` |
| Accessibility | WCAG 2.2 AA | `axe-core`, Lighthouse |
| Bundle size | <200KB initial | `bundlephobia` |
| Lighthouse score | >90 all categories | Lighthouse CI |

---

## Common Failure Modes

| Failure Mode | Symptom | Resolution |
|---|---|---|
| **Hardcoded strings** | No i18n | Use translation keys |
| **No error handling** | Silent failures | Add error boundaries |
| **Accessibility violations** | No keyboard nav, low contrast | Run axe-core |
| **API mismatch** | Type errors with backend | Generate from OpenAPI |
| **State sync issues** | Stale data | Use TanStack Query invalidation |
| **No loading states** | Blank screens | Add skeletons/spinners |

---

## Implementation Guidelines

### Component Pattern

```tsx
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@splash/ui";
import { membershipApi } from "@/api/membership";

interface MembershipCardProps {
  membershipId: string;
}

export function MembershipCard({ membershipId }: MembershipCardProps) {
  const { t } = useTranslation("membership");
  const { data, isLoading, error } = useQuery({
    queryKey: ["membership", membershipId],
    queryFn: () => membershipApi.get(membershipId),
  });

  if (isLoading) {
    return <Card.Skeleton />;
  }

  if (error) {
    return (
      <Card>
        <Card.Error>{t("errors.loadFailed")}</Card.Error>
      </Card>
    );
  }

  return (
    <Card>
      <Card.Title>{data.planName}</Card.Title>
      <Card.Status status={data.status}>
        {t(`status.${data.status}`)}
      </Card.Status>
      {data.status === "frozen" && (
        <Card.Description>
          {t("frozen.until", { date: data.freezeEndDate })}
        </Card.Description>
      )}
    </Card>
  );
}
```

### API Client Pattern

```typescript
// src/api/membership.ts
import { apiClient } from "./client";
import type { Membership, FreezeMembershipRequest } from "./schemas";

export const membershipApi = {
  get: (id: string) =>
    apiClient.get<Membership>(`/memberships/${id}`),

  list: (params: { tenantId: string; status?: string }) =>
    apiClient.get<Membership[]>("/memberships", { params }),

  freeze: (id: string, request: FreezeMembershipRequest) =>
    apiClient.post<Membership>(`/memberships/${id}/freeze`, request),

  unfreeze: (id: string) =>
    apiClient.post<Membership>(`/memberships/${id}/unfreeze`),
};
```

---

## Collaboration Rules

### Hand-off from Architect Agent

1. Review API contract
2. Confirm mock data structures
3. Verify design system availability

### Hand-off to QA Agent

1. Confirm all UI states are implemented
2. Provide test scenarios
3. Explain responsive breakpoints

### Hand-off to Accessibility Review

1. Run axe-core automated tests
2. Document keyboard flow
3. Tag accessibility reviewer

### Escalation

- If API contract changes: escalate to Architect
- If design is ambiguous: escalate to Product
- If design system is missing components: escalate to Frontend Lead

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [Frontend Structure](../05-frontend/folder-structure.md)
- [Component Design](../05-frontend/component-design.md)
- [Accessibility](../05-frontend/accessibility.md)
- [PWA Strategy](../05-frontend/pwa-strategy.md)
- [Design Tokens](../05-frontend/design-tokens.md)
