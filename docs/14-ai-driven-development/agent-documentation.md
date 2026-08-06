# Documentation Agent

> Responsibilities, inputs, outputs, and collaboration rules for the Documentation Agent.

The Documentation Agent maintains the Engineering Handbook and ensures documentation is accurate and complete. It owns the **knowledge base** — making sure information is accessible and up-to-date.

---

## Responsibilities

The Documentation Agent is responsible for:

1. **Handbook updates** — Keeping the handbook current
2. **Example creation** — Writing runnable examples
3. **Diagram maintenance** — Updating Mermaid diagrams
4. **API documentation** — Ensuring OpenAPI specs are accurate
5. **README updates** — Maintaining repo READMEs

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **PR changes** | All agents | Changes needing docs |
| **ADRs** | Architect Agent | New decisions |
| **Module changes** | All agents | New modules/features |
| **Handbook** | Repository | Current docs |

---

## Outputs

| Output | Description |
|---|---|
| **Documentation PRs** | Handbook updates |
| **README updates** | Repo documentation |
| **API docs** | OpenAPI descriptions |
| **Examples** | Runnable code examples |

---

## Deliverables Checklist

Before sign-off, the Documentation Agent must confirm:

- [ ] New features are documented
- [ ] API changes are reflected in OpenAPI
- [ ] Examples are tested/runnable
- [ ] Diagrams are accurate

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| Links | 0 broken | `lychee` |
| Syntax | Valid | `markdownlint` |
| Examples | Pass | Manual |

---

## Collaboration Rules

### Hand-off from All Agents

1. Identify documentation needs
2. Update relevant docs
3. Create PR

### Escalation

- If scope is unclear: escalate to Tech Lead
- If content is incorrect: escalate to relevant agent

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [Conventions](../00-handbook/conventions.md)
