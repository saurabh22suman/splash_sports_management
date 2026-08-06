# Zero Trust Architecture

> This document outlines our zero trust implementation: verify explicitly, least privilege, assume breach principles.

Zero trust means no implicit trust based on network location. Every request is authenticated and authorized, regardless of origin.

---

## Core Principles

| Principle | Implementation |
|---|---|
| **Verify explicitly** | Authenticate every request, no trust based on network |
| **Least privilege** | Minimum permissions, just-in-time access |
| **Assume breach** | Design for compromise, limit blast radius |

---

## Implementation

### Service-to-Service Authentication

All service communication uses mTLS:

```yaml
# Istio mTLS configuration
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

### Per-Request Authorization

Each request carries its own credentials:

```python
# Every internal request includes service identity
def make_internal_request(service: str, path: str):
    # Get service's own JWT
    service_token = get_service_token(service)

    return requests.get(
        f"http://{service}/api/v1/{path}",
        headers={
            "Authorization": f"Bearer {service_token}"
        }
    )
```

### Network Segmentation

```yaml
# Kubernetes NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-isolation
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-gateway
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
```

---

## Example: Service Mesh Authorization

```yaml
# AuthorizationPolicy
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: booking-service
spec:
  selector:
    matchLabels:
      app: booking-service
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/default/sa/api-gateway"]
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/api/v1/*"]
```

---

## Cross-Reference

- [Authentication](authentication.md) — Identity verification
- [Authorization & RBAC](authorization-rbac.md) — Access control
- [Tenant Isolation](tenant-isolation.md) — Data isolation
