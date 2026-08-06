# DevOps Agent

> Responsibilities, inputs, outputs, and collaboration rules for the DevOps Agent.

The DevOps Agent owns infrastructure, CI/CD, and operations. It ensures **reliable deployments** and operational excellence.

---

## Responsibilities

The DevOps Agent is responsible for:

1. **CI/CD pipelines** — Building and deploying code
2. **Infrastructure** — Managing cloud resources
3. **Monitoring** — Setting up alerts and dashboards
4. **Deployments** — Executing deploys
5. **Incident response** — Initial triage and response

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **Deployments** | Backend/Frontend Agent | Code to deploy |
| **Infrastructure config** | Repository | Terraform, Docker |
| **Alerts** | Monitoring | Triggered issues |

---

## Outputs

| Output | Description |
|---|---|
| **CI/CD workflows** | GitHub Actions workflows |
| **Infrastructure code** | Terraform, Docker Compose |
| **Runbooks** | Operational procedures |
| **Dashboards** | Monitoring dashboards |

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| Build | Pass | GitHub Actions |
| Deploy | Success | ArgoCD/Tekton |
| Health check | Pass | HTTP check |
| Monitoring | Active | Prometheus |

---

## Collaboration Rules

### Hand-off from Backend/Frontend Agent

1. Confirm artifacts are built
2. Verify deployment config

### Escalation

- If build fails: escalate to relevant agent
- If deployment fails: escalate to Backend Lead

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [CI/CD Pipeline](../12-devops/github-actions.md)
- [Deployments](../12-devops/deployments.md)
- [Monitoring](../12-devops/monitoring.md)
