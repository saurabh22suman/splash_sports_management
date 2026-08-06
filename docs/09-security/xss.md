# Cross-Site Scripting (XSS) Prevention

> This document covers ourXSS prevention strategy, including React's default escaping, Content Security Policy (CSP), and sanitization for user-generated HTML content.

Cross-Site Scripting (XSS) allows attackers to inject malicious scripts into web pages viewed by other users. XSS is particularly dangerous in our platform because authenticated users trust the application with their sessions. We prevent XSS through multiple layers: framework defaults, CSP headers, and sanitization for edge cases.

---

## Primary Defense: React's Default Escaping

React escapes content by default. When you render dynamic content in JSX, React automatically encodes it:

```jsx
// This is safe - React escapes 'userInput'
function UserDisplay({ userInput }) {
  return <div>{userInput}</div>;
}

// This renders as text, not HTML:
// <div>&lt;script&gt;alert('xss')&lt;/script&gt;</div>
```

> **Rule** — Never bypass React's escaping unless absolutely necessary and reviewed.

---

## Prohibited: dangerouslySetInnerHTML

Using `dangerouslySetInnerHTML` bypasses React's escaping and is a major XSS vector:

### Anti-pattern (NEVER DO THIS)

```jsx
// NEVER - allows XSS
function DisplayContent({ html }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

// User submits: <img src=x onerror=alert('xss')>
// This executes in every viewer's browser
```

### Correct Pattern

If you must render HTML, sanitize it first:

```jsx
import DOMPurify from 'dompurify';

function SafeHtmlDisplay({ html }) {
  const sanitized = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p', 'br'],
    ALLOWED_ATTR: []
  });
  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}
```

> **Rule** — Any use of `dangerouslySetInnerHTML` requires security review and must be paired with strict sanitization.

---

## Content Security Policy (CSP)

We enforce a strict Content Security Policy that prevents inline script execution and restricts resource loading:

### Headers

```
Content-Security-Policy:
  default-src 'none';
  script-src 'self';
  style-src 'self' 'nonce-{random}';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' https://api.splashh.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  upgrade-insecure-requests;
```

### Implementation in FastAPI

```python
from fastapi import Response
from fastapi.middleware.base import BaseHTTPMiddleware

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Generate nonce for this request
        import secrets
        nonce = secrets.token_hex(16)

        # Set CSP header
        csp = (
            "default-src 'none'; "
            "script-src 'self'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.splashh.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests"
        )
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        return response
```

### Nonce-Based Inline Scripts

If you must have inline scripts (rare), use the nonce:

```jsx
// In your server-rendered template
function Layout({ children, nonce }) {
  return (
    <html>
      <head>
        <script nonce={nonce}>
          // This script will execute because it has the valid nonce
          console.log('Trusted inline script');
        </script>
      </head>
      <body>{children}</body>
    </html>
  );
}
```

> **Why strict CSP** — CSP is our most effective XSS defense. If an attacker manages to inject a script tag, CSP blocks it from executing because inline scripts are disabled by default.

---

## Additional XSS Protections

### Output Encoding at Boundaries

We encode data contextually at system boundaries:

| Context | Encoding | Example |
|---|---|---|
| HTML | HTML entities | `<` → `&lt;` |
| JavaScript | JSON or escape | Use `JSON.stringify()` |
| URL | URL encoding | Use `encodeURIComponent()` |
| CSS | CSS escape | Rarely needed |

```python
import html

def encode_for_html(untrusted: str) -> str:
    """Encode string for safe HTML rendering."""
    return html.escape(untrusted)
```

### HTTP Security Headers

```python
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-XSS-Protection"] = "0"  # Disable, CSP handles it
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
```

### React Frontend: Additional Protections

```jsx
// Install DOMPurify for user input sanitization
// npm install dompurify

// Use it in any component that accepts user HTML
import DOMPurify from 'dompurify';

// Configure for strict mode
DOMPurify.setConfig({
  ALLOWED_TAGS: [],  // Start with nothing, add as needed
  ALLOWED_ATTR: [],
  FORBID_TAGS: ['script', 'style', 'iframe'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick']
});
```

---

## Testing XSS Prevention

### 1. Automated Scanning

We use OWASP ZAP for automated XSS testing:

```bash
# ZAP baseline scan
zap-baseline.py -t https://staging.splashh.com -r report.html
```

### 2. Code Review

Check for:
- `dangerouslySetInnerHTML` usage
- `innerHTML` assignments
- Event handlers with dynamic content
- URL parameters reflected in page

### 3. Manual Testing

Common XSS payloads to test:

```text
<script>alert('xss')</script>
<img src=x onerror=alert('xss')>
<svg onload=alert('xss')>
javascript:alert('xss')
<iframe src="javascript:alert('xss')">
```

---

## Cross-Reference

- [Output Encoding](output-encoding.md) — Context-aware encoding
- [API Security](api-security.md) — Input validation at API layer
- [Security Testing](security-testing.md) — Automated scanning
