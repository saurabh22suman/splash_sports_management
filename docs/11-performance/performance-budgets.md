# Performance Budgets

> Performance budgets as CI checks. Bundle size per route. LCP/INP/CLS in Lighthouse CI. API P95 latency. Error budget burn rate alerts.

This document establishes performance budgets for the Splashh Sports Platform. We enforce performance targets in CI to prevent regressions.

---

## Budget Categories

| Category | Budget | Alert Threshold |
|----------|--------|----------------|
| Initial JS bundle | 200KB | 250KB |
| Route: Dashboard | 150KB | 200KB |
| Route: Booking | 100KB | 150KB |
| Route: Admin | 200KB | 300KB |
| CSS | 50KB | 75KB |
| Fonts | 100KB | 150KB |
| Images | 500KB/page | 750KB/page |

---

## Bundle Size Budget

### Vite Configuration

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-select'],
        },
      },
    },
    // Warning at 500KB, error at 1MB
    chunkSizeWarningLimit: 500,
  },
});
```

### Bundle Analysis in CI

```yaml
# .github/workflows/bundle-size.yml
name: Bundle Size Check

on: [pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Bundle analyzer
        run: npm run analyze

      - name: Check bundle size
        run: |
          BUNDLE_SIZE=$(du -k dist/assets/*.js | awk '{sum+=$1} END {print sum}')
          MAX_SIZE=500

          if [ "$BUNDLE_SIZE" -gt "$MAX_SIZE" ]; then
            echo "Bundle size $BUNDLE_SIZE KB exceeds budget of $MAX_SIZE KB"
            exit 1
          fi
```

---

## Core Web Vitals Budget

### Lighthouse CI Configuration

```yaml
# .github/workflows/lighthouse.yml
name: Lighthouse Performance

on: [push, pull_request]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: npm run build

      - name: Preview
        run: npm run preview &
        env:
          CI: true

      - name: Run Lighthouse
        uses: treosh/lighthouse-ci-action@v10
        with:
          urls: |
            http://localhost:4173/
            http://localhost:4173/bookings
            http://localhost:4173/facilities
          budgetPath: ./lighthouse-budget.json
          uploadArtifacts: true
```

```json
// lighthouse-budget.json
{
  "ci": {
    "assert": {
      "assertions": {
        "categories:performance": ["error", { "minScore": 0.9 }],
        "first-contentful-paint": ["error", { "maxNumericValue": 1500 }],
        "largest-contentful-paint": ["error", { "maxNumericValue": 2500 }],
        "cumulative-layout-shift": ["error", { "maxNumericValue": 0.1 }],
        "interaction-to-next-paint": ["error", { "maxNumericValue": 200 }],
        "total-byte-weight": ["error", { "maxNumericValue": 500000 }],
        "dom-size": ["error", { "maxNumericValue": 1500 }]
      }
    }
  }
}
```

---

## API Latency Budget

```yaml
# .github/workflows/api-latency.yml
name: API Latency Check

on: [pull_request]

jobs:
  latency:
    runs-on: ubuntu-latest
    steps:
      - name: Start API
        run: |
          docker-compose up -d api
          sleep 10

      - name: Run load test
        run: |
          # Test critical endpoints
          for i in {1..100}; do
            curl -w "%{time_total}\n" -o /dev/null -s \
              http://localhost:8000/api/v1/facilities
          done > latencies.txt

      - name: Check P95
        run: |
          P95=$(cat latencies.txt | sort -n | awk 'BEGIN{c=0} {a[c++]=$1} END{print a[int(c*0.95)]}')
          echo "P95 latency: $P95 seconds"

          # Convert to milliseconds and compare
          P95_MS=$(echo "$P95 * 1000" | bc)

          if (( $(echo "$P95_MS > 200" | bc -l) )); then
            echo "P95 latency exceeds 200ms budget"
            exit 1
          fi
```

---

## Error Budget

```yaml
# .github/workflows/error-budget.yml
name: Error Budget

on: [schedule]
  # Run daily at 6 AM

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Query SLO
        run: |
          # Query error rate for past 24 hours
          ERROR_RATE=$(curl -s -G \
            --data-urlencode 'query=sum(rate(http_requests_total{status=~"5.."}[24h])) / sum(rate(http_requests_total[24h]))' \
            http://prometheus:9090/api/v1/query \
            | jq -r '.data.result[0].value[1]')

          # Calculate error budget (99.9% availability = 0.1% error budget)
          # 24 hours = 86400 seconds
          # Budget = 86400 * 0.001 = 86.4 seconds of errors
          BUDGET=$(echo "86400 * 0.001" | bc)
          ACTUAL=$(echo "$ERROR_RATE * 86400" | bc)

          echo "Error budget: $BUDRUPT seconds"
          echo "Actual errors: $ACTUAL seconds"

          if (( $(echo "$ACTUAL > $BUDGET" | bc -l) )); then
            echo "Error budget exhausted!"
            exit 1
          fi
```

---

## Synthetic Monitoring

```yaml
# .github/workflows/synthetic.yml
name: Synthetic Monitoring

on: [schedule]
  # Every 5 minutes

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Check endpoints
        run: |
          # Check critical endpoints
          curl -f -s -o /dev/null http://api.example.com/health || exit 1
          curl -f -s -o /dev/null http://api.example.com/api/v1/facilities || exit 1

      - name: Measure latency
        run: |
          TIME=$(curl -w "%{time_total}" -o /dev/null -s http://api.example.com/api/v1/facilities)
          echo "Response time: ${TIME}s"

          # Budget: 500ms
          if (( $(echo "$TIME > 0.5" | bc -l) )); then
            echo "Response time exceeds 500ms budget"
          fi
```

---

## Performance Budget Alerts

```yaml
# prometheus/alerts.yml
groups:
  - name: performance
    rules:
      - alert: BundleSizeWarning
        expr: |
          bundle_size_bytes > 500000
        for: 5m
        labels:
          severity: warning

      - alert: BundleSizeCritical
        expr: |
          bundle_size_bytes > 1000000
        for: 1m
        labels:
          severity: critical

      - alert: LighthouseScoreWarning
        expr: |
          lighthouse_performance_score < 0.9
        for: 30m
        labels:
          severity: warning

      - alert: APILatencyP95Warning
        expr: |
          histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 10m
        labels:
          severity: warning
```

---

## Trade-offs

| Budget | What we gain | What we give up |
|--------|--------------|-----------------|
| Bundle size | Fast initial load | Feature constraints |
| Web Vitals | Good UX | More optimization work |
| API latency | Responsive app | Engineering effort |
| Error budget | Reliability visibility | May block deploys |

---

## Related Documents

- [Performance](performance.md) — Frontend performance
- [Response Time Goals](response-time-goals.md) — API latency targets
- [Observability](observability.md) — Metrics and monitoring
