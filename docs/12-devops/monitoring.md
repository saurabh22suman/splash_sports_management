# Monitoring

> Prometheus + Grafana. SLI/SLO dashboards, burn rate alerts, per-service metrics.

This document defines our observability stack and alerting strategy. We prioritize actionable alerts (runbooks attached), SLO-focused monitoring (user experience), and service-level dashboards.

---

## Observability Stack

| Component | Purpose | Deployment |
|---|---|---|
| Prometheus | Metrics collection & storage | Kubernetes |
| Grafana | Visualization & dashboards | Kubernetes |
| Alertmanager | Alert routing & notification | Kubernetes |
| PagerDuty | On-call scheduling & escalation | SaaS |
| OpenTelemetry | Instrumentation | In-app |

---

## SLI/SLO Definitions

We define SLIs (Service Level Indicators) for each service:

### Backend API

| SLI | Definition | SLO Target |
|---|---|---|
| Availability | `sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m]))` | 99.9% |
| Latency (P50) | `histogram_quantile(0.50, http_request_duration_seconds_bucket)` | < 100ms |
| Latency (P95) | `histogram_quantile(0.95, http_request_duration_seconds_bucket)` | < 300ms |
| Latency (P99) | `histogram_quantile(0.99, http_request_duration_seconds_bucket)` | < 1s |
| Error rate | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | < 0.1% |

### Database

| SLI | Definition | SLO Target |
|---|---|---|
| Query latency (P95) | `pg_stat_statements` query time | < 200ms |
| Connection pool | Pool utilization | < 80% |
| Replication lag | Replica lag in seconds | < 5s |

### Redis

| SLI | Definition | SLO Target |
|---|---|---|
| Operation latency (P95) | Redis command duration | < 10ms |
| Memory usage | Used memory / maxmemory | < 80% |
| Eviction rate | Evicted keys / second | < 1/s |

---

## SLO Dashboard

```promql
# Availability (last 30 days)
1 - (
  sum(rate(http_requests_total{status=~"5..", service="backend"}[30d]))
  /
  sum(rate(http_requests_total{service="backend"}[30d]))
)
```

```promql
# Request volume by endpoint
sum(rate(http_requests_total{service="backend"}[5m])) by (endpoint, method)
```

```promql
# Error budget remaining
(
  1 - (
    sum(rate(http_requests_total{status=~"5..", service="backend"}[30d]))
    /
    sum(rate(http_requests_total{service="backend"}[30d]))
  )
) - 0.999  # Budget consumed
```

---

## Burn Rate Alerts

We alert on burn rate to catch SLO breaches before they happen:

```yaml
# prometheus/alerts.yaml
groups:
  - name: backend-slo
    interval: 30s
    rules:
      # Burn rate alert: 5-minute window, 1.01x error budget consumption
      - alert: BackendErrorBudgetBurn
        expr: |
          (
            sum(rate(http_requests_total{status=~"5..", service="backend"}[5m]))
            /
            sum(rate(http_requests_total{service="backend"}[5m]))
          )
          > (0.01 * 1.01)
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Backend error budget burning fast"
          description: "Error rate is {{ $value | humanizePercentage }}, budget burning at 1.01x for 5m"
          runbook_url: "https://runbooks.splashh.com/error-budget-burn"

      # Longer window, slower burn
      - alert: BackendErrorBudgetBurnSlow
        expr: |
          (
            sum(rate(http_requests_total{status=~"5..", service="backend"}[1h]))
            /
            sum(rate(http_requests_total{service="backend"}[1h]))
          )
          > (0.01 * 1.01)
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Backend error budget burning slowly"
          description: "Error rate is {{ $value | humanizePercentage }}, budget burning at 1.01x for 1h"
```

---

## Per-Service Dashboards

Each service has a dedicated Grafana dashboard:

```json
{
  "title": "Backend API - Service Dashboard",
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{service='backend'}[5m])) by (endpoint)"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~'5..', service='backend'}[5m])) by (endpoint)"
        }
      ]
    },
    {
      "title": "Latency (P50, P95, P99)",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, http_request_duration_seconds_bucket{service='backend'})"
        },
        {
          "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket{service='backend'})"
        },
        {
          "expr": "histogram_quantile(0.99, http_request_duration_seconds_bucket{service='backend'})"
        }
      ]
    },
    {
      "title": "Database Connection Pool",
      "type": "gauge",
      "targets": [
        {
          "expr": "pg_stat_activity_count / pg_settings_max_connections"
        }
      ]
    }
  ]
}
```

---

## Alert Routing

Alerts route to PagerDuty based on severity and service:

```yaml
# alertmanager/config.yaml
route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    # Critical alerts: immediate page
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: true

    # Warning alerts: notify channel, escalate if no ack
    - match:
        severity: warning
      receiver: 'slack-warnings'
      continue: true

    # Info alerts: just log
    - match:
        severity: info
      receiver: 'null'

receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '{{ .Env.PAGERDUTY_SERVICE_KEY }}'
        severity: critical
        description: "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}"
        details:
          service: "{{ range .Alerts }}{{ .Labels.service }}{{ end }}"
          runbook: "{{ range .Annotations.runbook_url }}{{ . }}{{ end }}"

  - name: 'slack-warnings'
    slack_configs:
      - channel: '#alerts-warnings'
        title: "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}"
        text: "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
```

---

## Runbooks

Every alert must have a runbook. Runbooks are linked in the alert annotation:

```markdown
# Runbook: Error Budget Burn

## Symptoms
- Error rate exceeds 1% for 5+ minutes
- SLO dashboard shows budget burning faster than expected

## Impact
- Users experiencing errors
- Error budget depleting faster than anticipated

## Diagnosis
1. Check which endpoints are failing:
   ```promql
   sum(rate(http_requests_total{status=~"5..", service="backend"}[5m])) by (endpoint)
   ```

2. Check recent deployments:
   ```bash
   kubectl rollout history deployment/backend -n production
   ```

3. Check logs for errors:
   ```bash
   kubectl logs -n production -l app=backend --tail=100 | grep ERROR
   ```

## Resolution
1. If caused by recent deploy: rollback immediately
2. If database issue: check connection pool and slow queries
3. If external service: check status pages and contact them

## Escalation
- If unresolved in 15 minutes: page on-call engineer
- If data corruption suspected: page DBA
```

---

## Key Metrics to Record

Every service must expose:

| Metric | Type | Purpose |
|---|---|---|
| `http_requests_total` | Counter | Request volume |
| `http_request_duration_seconds` | Histogram | Latency distribution |
| `http_requests_total{status=~"5.."}` | Counter | Error counting |
| `app_booking_duration_seconds` | Histogram | Business operation duration |
| `db_pool_connections` | Gauge | Connection pool usage |
| `redis_operation_duration_seconds` | Histogram | Cache performance |

---

## Summary

| Component | Implementation |
|---|---|
| Metrics | Prometheus |
| Dashboards | Grafana |
| Alerts | Alertmanager → PagerDuty |
| SLO targets | 99.9% availability, < 300ms P95 |
| Alert on | Burn rate, not just thresholds |
| Runbooks | Required for every alert |

---

## Related Documents

- [Logging](./logging.md) — Log aggregation
- [Tracing](./tracing.md) — Distributed tracing
- [Rollback Strategy](./rollback-strategy.md) — Incident response
- [Alerting Runbook Template](../09-security/incident-response.md) — Template
