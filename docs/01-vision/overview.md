# Platform Vision

> What we are building, who it serves, and how we measure success.

---

## Mission

To give every sports club — from a single facility to a national chain — a single, reliable, secure platform to run their day-to-day operations: members, bookings, payments, coaches, and communications.

We start with **Splashh Sports Club** as our first tenant and design from day one to onboard hundreds more without rewriting the platform.

---

## Product scope

### First-class sports

The platform must support these sports **without significant code changes** — only configuration:

- Swimming
- Badminton
- Tennis
- Pickleball
- Gym (incl. group classes)
- Cricket Nets
- Football
- Indoor Games (table tennis, snooker, carrom, etc.)
- Coaching Academies (recurring lessons)

> **Why configuration over code?** New sports have similar primitives: a facility, a slot, a price, a coach, a customer, a booking. We model these primitives once and parameterize everything else.

### First-class capabilities

| Capability | Description |
|---|---|
| Member management | Profiles, guardians, waivers, KYC |
| Memberships | Plans, subscriptions, renewals, freezes, cancellations |
| Facility management | Resources (courts, pools, gyms), availability, blackout dates |
| Booking | Slot reservation, recurring bookings, group bookings, waitlists |
| Check-in | QR / OTP / NFC |
| Payments | Pricing, taxes, invoices, refunds, splits, dunning |
| Coaches | Schedules, classes, payroll inputs |
| Notifications | SMS, email, push, in-app, WhatsApp (via integrations) |
| Reports | Bookings, revenue, utilization, retention |
| Admin | RBAC, audit, tenant settings, branding |
| Integrations | Payment gateways, SMS providers, accounting, calendars |

### Out of scope (v1)

- Live streaming of matches.
- Social features (feeds, posts, comments).
- AI-generated content.
- Marketplace for third-party coaches.
- Native mobile apps (we ship a PWA).

---

## Success metrics

We measure success across four axes:

### 1. Operational reliability

| Metric | Target |
|---|---|
| API uptime | 99.9% |
| P95 API latency | < 200 ms |
| Failed-booking rate | < 0.1% |
| Booking race-condition incidents | 0 (zero) |
| Data loss tolerance (RPO) | 5 minutes |
| Recovery time (RTO) | 1 hour |

### 2. Multi-tenant adoption

| Metric | Year 1 | Year 3 |
|---|---|---|
| Active tenants | 1 (Splashh) | 50 |
| Total members under management | 5,000 | 200,000 |
| Bookings per month | 30,000 | 1.5M |

### 3. Engineering velocity

| Metric | Target |
|---|---|
| Mean time to merge (small PR) | < 1 business day |
| Change failure rate | < 10% |
| Mean time to recovery (MTTR) | < 30 minutes |
| Test coverage — domain | ≥ 95% |
| Test coverage — services | ≥ 90% |
| Test coverage — API | ≥ 80% |

### 4. Security posture

| Metric | Target |
|---|---|
| OWASP ASVS level | Level 2 |
| Cross-tenant data leakage incidents | 0 |
| Pen test criticals open | 0 |
| Mean time to patch critical CVE | < 7 days |

---

## Stakeholders

| Stakeholder | Primary concerns |
|---|---|
| Splashh operations team | Day-to-day usability, no downtime during peak hours |
| Splashh finance | Accurate invoices, reconcilable payments, clean reports |
| Splashh coaches | Easy schedule access, attendance, payouts |
| Splashh members | Fast booking, transparent pricing, fair cancellation |
| Future tenants | Easy onboarding, white-labeling, no shared infrastructure noise |
| Engineering team | Maintainable code, low on-call burden, clear ownership |
| Security & compliance | OWASP alignment, audit trails, regulatory compliance |

---

## Constraints

### Business constraints

- **Single-region launch**, with architecture designed to expand to multi-region.
- **Cost-sensitive**: we prefer boring, well-supported technology over cutting-edge.
- **AI-assisted from day one** — agents are first-class collaborators in the dev lifecycle.

### Technical constraints

- **No proprietary lock-in** for core infrastructure (Postgres, Redis are open source).
- **PWA-first** — no native mobile apps in v1.
- **Offline-tolerant customer PWA** — bookings can be queued when connectivity is poor.

### Regulatory constraints

- **DPDPA (India)** compliance for personal data.
- **PCI-DSS** compliance for payment data (via tokenization, never storing PAN/CVV).
- **RBI guidelines** for recurring payments and stored credentials.

---

## What success looks like in 5 years

- **200+ active tenants** across India, operating multiple sports.
- **>5M members** under management.
- **A team of 25–50 engineers** working productively, with AI agents handling significant chunks of routine work.
- **A platform that is still enjoyable to work on** — code is readable, tests pass, incidents are rare, and the handbook remains accurate.

---

## How this document relates to the rest of the handbook

- [Engineering Philosophy](./principles.md) — the values and heuristics that drive day-to-day decisions.
- [Architecture](../02-architecture/system-context.md) — the structural realization of this vision.
- [Modules](../18-modules/README.md) — the bounded contexts that map to product capabilities.
