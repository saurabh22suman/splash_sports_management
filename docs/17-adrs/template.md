# ADR Template

> MADR-style Architecture Decision Record template.

This template follows the MADR (Markdown Architectural Decision Records) format. Use this template for all new ADRs.

---

## Template

```markdown
# ADR-[NUMBER]: [Title]

## Status
Proposed | Accepted | Deprecated | Rejected

## Context
[Describe the context and problem statement. What is the background? Why is this decision needed?]

## Decision
[Describe the decision that was made. What are we doing?]

## Consequences
### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Downside 1]
- [Downside 2]

### Neutral
- [Neutral consequence 1]

## Alternatives Considered
### Alternative 1: [Name]
[Description and why it was rejected]

### Alternative 2: [Name]
[Description and why it was rejected]

## References
- [Reference 1]
- [Reference 2]

## Notes
[Any additional notes, open questions, or follow-up items]
```

---

## Guidelines

### When to Create an ADR

Create an ADR when a decision:
- Affects module boundaries
- Introduces new technology
- Changes API contract
- Impacts security model
- Affects performance significantly
- Sets precedent for future decisions

### ADR Numbering

- Use sequential numbering: ADR-0001, ADR-0002, etc.
- Numbers are never reused
- Deprecated ADRs keep their number with "Deprecated" status

### Writing Style

- Be concise — each section should be 2-4 sentences
- Be specific — avoid vague language
- Be factual — focus on trade-offs, not opinions

---

## Example ADR

See [ADR-0001: Modular Monolith](./0001-modular-monolith.md) for a complete example.

---

## Related Documents

- [ADR Index](./index.md)
- [Architecture Overview](../02-architecture/overview.md)
