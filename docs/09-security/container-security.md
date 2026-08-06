# Container Security

> This document details our container security strategy, including image hardening, non-root users, read-only filesystems, vulnerability scanning, and image signing.

Containers are the deployment unit for our platform. A compromised container can provide an attacker with access to the cluster, secrets, and data. We harden every layer of our container security: base images, runtime configuration, and continuous scanning.

---

## Base Images: Distroless

We use **distroless** base images that contain only the application and its runtime dependencies — no shell, package managers, or unnecessary tools:

```dockerfile
# Backend: distroless python
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/dependencies -r requirements.txt

FROM gcr.io/distroless/python3-debian12
COPY --from=builder /dependencies /dependencies
COPY . /app
WORKDIR /app

# No shell, no package manager, minimal attack surface
CMD ["main:app"]
```

```dockerfile
# Frontend: distroless nginx
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM gcr.io/distroless/nginx-debian12
COPY --from=builder /app/dist /usr/share/nginx/html
# Config and static files only
CMD ["nginx", "-g", "daemon off;"]
```

> **Why distroless** — Traditional images (ubuntu, alpine) include shells, package managers, and utilities that attackers can use to escalate privileges. Distroless images have a minimal attack surface and smaller vulnerability footprint.

---

## Non-Root User

Every container runs as a non-root user:

```dockerfile
FROM gcr.io/distroless/python3-debian12

# Create app user
RUN adduser --system --group appuser

# Change ownership
COPY --chown=appuser:appuser . /app
WORKDIR /app

# Switch to non-root user
USER appuser

CMD ["main:app"]
```

> **Rule** — No container may run as root in production. Use `USER appuser` in every Dockerfile.

---

## Read-Only Filesystem

Containers run with read-only filesystems where possible:

```yaml
# kubernetes/pod.yaml
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10000
    fsGroup: 10000
  containers:
    - name: backend
      image: splashh/backend:latest
      securityContext:
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: false
        capabilities:
          drop:
            - ALL
      volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/.cache
```

### Volumes for Write Access

| Path | Purpose | Mount Type |
|---|---|---|
| `/tmp` | Temp files | emptyDir |
| `/app/.cache` | Application cache | emptyDir |
| `/var/log` | Log files | emptyDir |
| `/var/run` | Runtime files | emptyDir |

---

## Image Scanning: Trivy

We scan every image before deployment using **Trivy**:

```yaml
# .github/workflows/image-scan.yml
name: Container Scanning

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

jobs:
  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t splashh/backend:${{ github.sha }} .

      - name: Run Trivy scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'image'
          image-ref: 'splashh/backend:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload results to GitHub
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

### Vulnerability Thresholds

| Severity | Blocking | Action |
|---|---|---|
| Critical | Yes | Block deployment, page on-call |
| High | Yes (in main) | Block deployment, fix in 7 days |
| Medium | No | Warn, fix in 30 days |
| Low | No | Track, fix in next cycle |

---

## Image Signing: cosign

We sign container images using **cosign** (Sigstore):

```yaml
# .github/workflows/sign.yml
name: Sign Images

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and push image
        run: |
          docker build -t splashh/backend:${{ github.sha }} .
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push splashh/backend:${{ github.sha }}

      - name: Sign image with cosign
        run: |
          cosign sign --yes splashh/backend:${{ github.sha }}
        env:
          COSIGN_EXPERIMENTAL: "1"

      - name: Verify signature
        run: |
          cosign verify splashh/backend:${{ github.sha }}
```

### cosign Verification in Kubernetes

```yaml
# kubernetes/kyverno-policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-signed-images
spec:
  validationFailureAction: enforce
  rules:
    - name: check-image-signature
      match:
        resources:
          kinds:
            - Pod
      verifyImages:
        - image: "ghcr.io/splashh/*"
          attestors:
            - keyless:
                url: https://fulcio.sigstore.dev
                identity: .subject == "https://github.com/splashh/sports-management"
```

---

## Vulnerability Remediation SLA

| Severity | Detect to Fix | Example |
|---|---|---|
| Critical | 7 days | RCE in base image |
| High | 30 days | Privilege escalation |
| Medium | 90 days | Information disclosure |
| Low | Next release | Minor issues |

---

## Container Security Best Practices

| Practice | Implementation |
|---|---|
| Minimal base image | Distroless (no shell) |
| Non-root user | USER directive in Dockerfile |
| Read-only filesystem | securityContext.readOnlyRootFilesystem |
| Drop capabilities | capabilities.drop: ALL |
| No privilege escalation | allowPrivilegeEscalation: false |
| Image scanning | Trivy in CI |
| Image signing | cosign |
| No secrets in image | Use external secrets operator |
| Minimal layers | Multi-stage builds |

---

## Cross-Reference

- [Dependency Scanning](dependency-scanning.md) — Dependency vulnerabilities
- [Supply Chain](supply-chain.md) — SLSA framework
- [Secrets Management](secrets-management.md) — Secret injection
