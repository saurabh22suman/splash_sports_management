# Performance Gates

> Performance-specific quality requirements.

Performance gates ensure the system meets latency, throughput, and resource usage targets.

---

## Gate List

| Gate | Tool | Threshold | Stage |
|---|---|---|---|
| Bundle Size | webpack-bundle-analyzer | <200KB initial | PR |
| Lighthouse CI | Lighthouse | >90 all categories | PR |
| API Latency | k6 | P95 <200ms | Release |
| Load Test | k6 | Pass at 2x expected | Release |
| Database Query | Query analysis | P95 <100ms | PR + Release |

---

## Bundle Size Budget

```javascript
// webpack.config.js
module.exports = {
  performance: {
    maxEntrypointSize: 200000,  // 200KB
    maxAssetSize: 200000,
  },
};
```

---

## Lighthouse CI

```yaml
# .github/workflows/lighthouse.yml
name: Lighthouse

on: [pull_request]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm install && npm run build
      - run: npm install -g @lhci/cli
      - run: lhci autorun
```

---

## API Latency Test

```javascript
// k6/api-latency.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_duration: ['p(95)<200'],  // P95 < 200ms
  },
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 10,
      duration: '30s',
    },
  },
};

export default function () {
  const res = http.get('https://api.splashh.com/v1/bookings');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  });
  sleep(1);
}
```

---

## Load Test

```javascript
// k6/load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up
    { duration: '5m', target: 100 },  // Steady
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const payload = JSON.stringify({ member_id: '123' });
  const params = { headers: { 'Content-Type': 'application/json' } };

  http.post('https://api.splashh.com/v1/bookings', payload, params);
  sleep(1);
}
```

---

## Database Query Budget

```sql
-- Example query analysis
EXPLAIN ANALYZE
SELECT b.*, f.name as facility_name
FROM bookings b
JOIN facilities f ON b.facility_id = f.id
WHERE b.tenant_id = 'abc-123'
  AND b.date >= '2024-01-01'
ORDER BY b.date DESC
LIMIT 20;

-- P95 query time should be <100ms
```

---

## Performance Budget Enforcement

> **Rule** — Exceeding bundle size budget blocks PR merge. Exceeding API latency requires Tech Lead approval.

---

## Related Documents

- [Performance Overview](../11-performance/overview.md)
- [Performance Budgets](../11-performance/performance-budgets.md)
- [Load Tests](../10-testing/load-tests.md)
