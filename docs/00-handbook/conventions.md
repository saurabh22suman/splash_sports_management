# Handbook Conventions

> How this handbook is written, formatted, and maintained.

---

## Audience

This handbook assumes the reader:

- Is a **senior engineer**, **architect**, **AI coding agent**, **QA engineer**, or **DevOps engineer**.
- Has prior experience with **Python**, **TypeScript**, **PostgreSQL**, **Docker**, and **Git**.
- Does **not** need introductory material on HTTP, REST, or relational databases.
- Needs to make **defensible engineering decisions** under time pressure.

---

## Voice

- **Direct**, not promotional. We don't say *"leverages best-in-class paradigms"* — we say *"we use Postgres because …"*.
- **Opinionated**. Every decision has a default; deviation requires an ADR.
- **Trade-off aware**. We explain the cost of a decision, not just the benefit.
- **Future-aware**. We write for engineers who will read this in 2027, 2029, and beyond.

---

## Formatting

### Callouts

We use blockquote callouts for emphasis:

> **Rule** — a binding rule. Violations require an ADR or an explicit override in the PR description.
>
> **Guideline** — a strong recommendation. Deviate only with justification in code review.
>
> **Anti-pattern** — something we explicitly avoid. If you see this in a PR, request a change.
>
> **Why** — the rationale behind a non-obvious decision. Read this before proposing an alternative.
>
> **Pitfall** — a recurring mistake we've seen; calling it out so you avoid it.

### Code blocks

- Code blocks are **real and runnable** unless they begin with the comment `# illustrative`.
- File paths are shown in headers above the code block:

```python title="apps/backend/src/booking/service.py"
async def create_booking(...)
```

- Shell commands assume the repo root as the working directory.

### Diagrams

- All diagrams are **Mermaid**. They render in GitHub, GitLab, VS Code, and most Markdown viewers.
- Diagrams are not decorative — they must reflect the current code. PRs that change architecture update diagrams in the same PR.

### Tables

We use tables to summarize:

- **Decision matrices** — options, criteria, scores.
- **Comparison tables** — alternatives, trade-offs.
- **Checklists** — things to do before moving to the next step.

### Cross-references

- All cross-references use **relative paths**.
- Keep folder structure intact when moving files.

---

## Document structure

Each top-level document follows this skeleton:

```markdown
# Title

> One-paragraph summary of what this document is and why it exists.

## When to read this
## When NOT to read this
## Principles
## Patterns
## Anti-patterns
## Examples
## Related documents
```

Smaller reference docs (e.g. naming conventions) are free to use a tighter structure.

---

## Required sections for module docs

Each module doc in `18-modules/` must include:

1. **Purpose** — what the module does, in one paragraph.
2. **Aggregates** — aggregate roots owned by this module.
3. **Public APIs** — list of endpoints exposed by this module.
4. **Events** — events this module publishes and consumes.
5. **Dependencies** — other modules this module depends on, and how.
6. **Invariants** — business rules this module must enforce.
7. **Open questions** — anything ambiguous or unresolved.

---

## Required sections for ADRs

ADRs use the [MADR](https://adr.github.io/madr/) template — see [ADR Template](../17-adrs/template.md). Every ADR must capture:

- **Context** — what forces are at play.
- **Decision** — what we chose.
- **Consequences** — what becomes easier, what becomes harder.
- **Alternatives considered** — at least two alternatives with reasons for rejection.

---

## How to write a new document

1. Decide which section it belongs in. If none fits, propose a new section in the PR.
2. Follow the document structure above.
3. Add cross-references to related docs.
4. Add the document to the [README](../README.md) table of contents.
5. Open a PR. Reviewer checks for: accuracy, completeness, consistency with linked docs.

---

## How to propose a material change

1. Open an issue describing the change.
2. Update the relevant document(s).
3. If the change adds, removes, or inverts a **Rule**, write or update an **ADR**.
4. Request review from the section owner (see README status table).
5. After merge, update the changelog at the bottom of the document if it was a significant change.

---

## What we deliberately avoid in this handbook

- **Tutorial-style content**. We assume prior knowledge.
- **Tool evangelism**. We mention a tool because we chose it, not because it's trendy.
- **Marketing language** ("world-class", "cutting-edge", "blazing-fast").
- **Restating what code already says**. Code is the source of truth; docs explain intent.
- **Speculative architecture**. If it's not in the code or planned, it's not in the handbook.

---

## Versioning

- The handbook has **no formal version number**. It is always current.
- Material changes are recorded as ADRs.
- The git history of any document is the change log.
