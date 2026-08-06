# Supply Chain Security

> This document details our supply chain security strategy, aligning with SLSA, signed commits, signed images, and dependency management.

We implement the SLSA (Supply-chain Levels for Software Artifacts) framework to protect against supply chain attacks.

---

## SLSA Framework

| Level | Requirement | Our Status |
|---|---|---|
| **Level 1** | Build process documentation | Complete |
| **Level 2** | Signed builds, provenance | Complete |
| **Level 3** | Hardened builds, hermetic builds | In Progress |
| **Level 4** | Security reviews, attestations | Target |

---

## Signed Commits

We require signed commits:

```bash
# Configure Git for signed commits
git config commit.gpgsign true
git config user.signingkey KEY_ID
```

### GPG Key Requirements

- 4096-bit RSA key
- Key stored in HSM or secure storage
- Key rotation every 2 years

---

## Signed Images (cosign)

We sign all container images:

```bash
# Sign image
cosign sign --yes splashh/backend:latest

# Verify image
cosign verify splashh/backend:latest
```

---

## Dependency Pinning

We pin all dependencies:

```toml
# requirements.txt
fastapi==0.109.0
sqlalchemy==2.0.25
pydantic==2.5.3
```

```json
// package-lock.json
// Generated with exact versions
```

---

## Private Registry

All dependencies come from approved sources:

| Registry | Purpose |
|---|---|
| PyPI | Python packages |
| npmjs.com | JavaScript packages |
| GHCR.io | Internal images |
| public.ecr.aws | AWS-maintained images |

---

## Cross-Reference

- [Container Security](container-security.md) — Image security
- [Dependency Scanning](dependency-scanning.md) — Vulnerability scanning
- [Secrets Management](secrets-management.md) — Secret handling
