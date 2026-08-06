# Password Policy

> This document defines our password requirements, including length, breach detection, lockout policies, and alignment with NIST 800-63B guidelines.

We follow modern password security best practices from NIST 800-63B, focusing on length over complexity.

---

## Password Requirements

| Requirement | Value | Rationale |
|---|---|---|
| Minimum length | 12 characters | NIST recommendation |
| Maximum length | 128 characters | Prevent DoS |
| Complexity | Not required | Per NIST — complexity rules don't improve security |
| Breach check | Mandatory | Reject compromised passwords |
| Periodic reset | Not required | Per NIST — leads to weaker passwords |

---

## Why Length Over Complexity

Traditional complexity rules (uppercase, lowercase, numbers, symbols) lead to predictable patterns:

- `P@ssw0rd1!` — passes complexity, easily guessed
- `correct horse battery staple` — 28 chars, easy to remember, harder to crack

> **Why** — Entropy (randomness) matters more than character set. A 25-character passphrase has more entropy than an 8-character complex password.

---

## Breach Detection

```python
import hashlib
import httpx

def check_password_breached(password: str) -> bool:
    """Check password against HIBP using k-anonymity."""
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    response = httpx.get(
        f"https://api.pwnedpasswords.com/range/{prefix}",
        timeout=5.0
    )

    for line in response.text.splitlines():
        hash_suffix, count = line.split(":")
        if hash_suffix == suffix:
            return True  # Found in breach

    return False
```

---

## Account Lockout

| Parameter | Value |
|---|---|
| Failed attempts | 10 |
| Lockout duration | 15 minutes |
| Reset | After lockout expires or successful login |

---

## Anti-Patterns We Avoid

- **Forced periodic password changes** — Leads to weaker passwords
- **Complexity requirements** — Not proven to improve security
- **Password hints** — Can reveal information
- **Security questions** — Easily bypassed

---

## Cross-Reference

- [Authentication](authentication.md) — Auth architecture
- [MFA](mfa.md) — Multi-factor authentication
- [HIBP Integration](authentication.md) — Breach detection
