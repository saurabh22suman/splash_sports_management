# Performance Agent

> Responsibilities, inputs, outputs, and collaboration rules for the Performance Agent.

The Performance Agent ensures the system meets performance requirements. It owns **performance budgets**, profiling, and load testing.

---

## Responsibilities

The Performance Agent is responsible for:

1. **Profiling** — Identifying performance bottlenecks
2. **Budget enforcement** — Ensuring bundle size, latency, and throughput meet targets
3. **Load testing** — Running synthetic load to validate capacity
4. **Cache optimization** — Advising on caching strategies
5. **Query optimization** — Reviewing slow queries
6. **Monitoring** — Setting up performance alerts

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **PR changes** | All agents | Changes to profile |
| **Performance budgets** | [Performance Budgets](../11-performance/performance-budgets.md) | Targets |
| **Architecture** | Architect Agent | System design |
| **Monitoring data** | [Observability](../11-performance/observability.md) | Current performance |

---

## Outputs

| Output | Description |
|---|---|
| **Performance reports** | Profiling results |
| **Budget compliance** | Pass/fail for budgets |
| **Load test results** | Capacity validation |
| **Optimization recommendations** | Suggested improvements |

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| Bundle size | <200KB initial | `webpack-bundle-analyzer` |
| API P95 latency | <200ms | APM |
| Lighthouse score | >90 | Lighthouse CI |
| Load test | Pass at 2x expected | `locust` |
| Database query | <100ms P95 | Query analysis |

---

## Collaboration Rules

### Hand-off from Backend/Frontend Agent

1. Profile changes
2. Run performance tests
3. Report findings

### Escalation

- If budget exceeded: escalate to Backend/Frontend Agent
- If infrastructure needed: escalate to DevOps

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [Performance Budgets](../11-performance/performance-budgets.md)
- [Performance Gates](../16-quality-gates/performance-gates.md)
