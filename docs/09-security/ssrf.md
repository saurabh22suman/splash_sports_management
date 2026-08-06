# Server-Side Request Forgery (SSRF) Prevention

> This document covers ourSSRF prevention strategy, including egress controls, URL allowlists, internal IP blocking, and safe URL fetching patterns.

Server-Side Request Forgery (SSRF) allows attackers to make the server perform requests to internal services, cloud metadata endpoints, or internal networks. This is particularly dangerous in cloud environments where metadata services (AWS IMDS, GCP metadata) contain sensitive credentials.

---

## Primary Defense: Egress Allowlist

We only allow outbound HTTP requests to pre-approved domains. All other destinations are blocked:

```python
from urllib.parse import urlparse
import ipaddress

# Approved domains for webhook delivery
ALLOWED_WEBHOOK_DOMAINS = {
    "api.stripe.com",
    "api.razorpay.com",
    "api.sendgrid.com",
    "hooks.slack.com"
}

# Blocked IP ranges (internal networks)
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.169.254/32"),  # AWS IMDS
    ipaddress.ip_network("metadata.google.internal/32"),  # GCP IMDS
    ipaddress.ip_network("127.0.0.1/32"),
    ipaddress.ip_network("::1/128"),  # IPv6 localhost
]

def is_url_allowed(url: str) -> tuple[bool, str]:
    """Validate URL against allowlist and blocked ranges."""
    try:
        parsed = urlparse(url)

        # Only allow http and https
        if parsed.scheme not in ("http", "https"):
            return False, f"Invalid scheme: {parsed.scheme}"

        # Check hostname against allowlist
        hostname = parsed.hostname
        if hostname and hostname not in ALLOWED_WEBHOOK_DOMAINS:
            return False, f"Domain not in allowlist: {hostname}"

        # Resolve and validate IP
        import socket
        ip_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_str)

        # Check against blocked ranges
        for blocked in BLOCKED_IP_RANGES:
            if ip in blocked:
                return False, f"IP in blocked range: {ip_str}"

        # DNS pinning: resolve once, use that IP
        # Do not follow redirects to untrusted domains

        return True, "Allowed"

    except Exception as e:
        return False, f"Validation error: {str(e)}"
```

> **Rule** — All outbound HTTP requests from the application must go through a URL validation function. No direct requests to user-provided URLs.

---

## Cloud Metadata Protection

We explicitly block access to cloud metadata endpoints:

| Cloud | Metadata IP | Data |
|---|---|---|
| AWS | 169.254.169.254 | Credentials, instance info |
| GCP | metadata.google.internal | Credentials, project info |
| Azure | 169.254.169.254 | Credentials, instance info |
| Kubernetes | 10.96.0.1 | Service account tokens |

```python
def block_imds(url: str) -> bool:
    """Block requests to Instance Metadata Service."""
    parsed = urlparse(url)
    hostname = parsed.hostname

    # Direct IP check
    if hostname == "169.254.169.254":
        return True

    # DNS resolution check
    try:
        ip = socket.gethostbyname(hostname)
        if ip.startswith("169.254."):
            return True
    except socket.gaierror:
        pass

    return False
```

---

## Safe URL Fetcher

We provide a safe HTTP client that enforces all SSRF protections:

```python
import httpx
from typing import Optional

class SafeHTTPClient:
    """HTTP client with SSRF protection."""

    def __init__(self, allowed_domains: set[str]):
        self.allowed_domains = allowed_domains

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> httpx.Response:
        """Fetch URL with SSRF protection."""
        allowed, reason = is_url_allowed(url)
        if not allowed:
            raise SSRFProtectionError(f"URL not allowed: {reason}")

        # Create client with restrictions
        async with httpx.AsyncClient(
            timeout=kwargs.pop("timeout", 30.0),
            follow_redirects=False,  # No redirect following
            **kwargs
        ) as client:
            response = await client.request(method, url)
            return response


class SSRFProtectionError(Exception):
    """Raised when URL fails SSRF validation."""
    pass
```

---

## Webhook Security

Webhooks are a common SSRF vector. We implement additional safeguards:

### 1. Signature Verification

```python
import hmac
import hashlib

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify webhook signature from provider."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)
```

### 2. Timeout and Size Limits

```python
# Never fetch large payloads from webhooks
MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB
REQUEST_TIMEOUT = 10  # seconds

async def fetch_webhook(url: str, timeout: float = 10.0):
    """Fetch webhook with size and time limits."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            timeout=timeout,
            follow_redirects=False
        )
        # Verify size before reading body
        if int(response.headers.get("content-length", 0)) > MAX_RESPONSE_SIZE:
            raise SSRFProtectionError("Response too large")

        content = response.read()
        if len(content) > MAX_RESPONSE_SIZE:
            raise SSRFProtectionError("Response too large")

        return content
```

---

## Testing SSRF Protection

### Test 1: Internal IP Access Blocked

```python
@pytest.mark.parametrize("url", [
    "http://127.0.0.1/admin",
    "http://192.168.1.1/database",
    "http://10.0.0.1/internal/api",
    "http://169.254.169.254/latest/meta-data",
])
def test_internal_ips_blocked(url):
    allowed, reason = is_url_allowed(url)
    assert allowed is False
    assert "blocked" in reason.lower()
```

### Test 2: Allowed Domains Work

```python
@pytest.mark.parametrize("url", [
    "https://api.stripe.com/v1/charges",
    "https://hooks.slack.com/services/xxx",
])
def test_allowed_domains(url):
    allowed, _ = is_url_allowed(url)
    assert allowed is True
```

### Test 3: DNS Rebinding Blocked

```python
def test_dns_rebinding_blocked():
    """Verify DNS rebinding attacks are blocked."""
    # Use a domain that could resolve to internal IPs
    allowed, _ = is_url_allowed("https://evil.example.com")
    # Should be blocked if domain not in allowlist
    # or IP resolves to internal range
```

---

## Cross-Reference

- [Secrets Management](secrets-management.md) — Secure secret storage
- [API Security](api-security.md) — Input validation
- [Output Encoding](output-encoding.md) — Context-aware encoding
