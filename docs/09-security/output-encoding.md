# Output Encoding

> This document details our output encoding strategy, covering context-aware encoding at system boundaries, framework defaults, and when custom encoding is required.

Output encoding converts untrusted data into a safe format before rendering. The correct encoding depends on the output context (HTML, JavaScript, URL, SQL, shell). We rely on framework defaults where possible and apply custom encoding only at system boundaries.

---

## Principle: Use Framework Defaults

Our primary defense is framework-provided escaping:

| Context | Framework | Default Behavior |
|---|---|---|
| HTML rendering | React | Auto-escapes JSX content |
| SQL queries | SQLAlchemy | Parameterized, auto-escapes |
| URL parameters | urllib | Auto-encodes |
| JSON API | FastAPI/Pydantic | JSON serialization |

> **Rule** — Do not manually escape data that the framework escapes automatically. Manual escaping can introduce inconsistencies and bypasses.

---

## React: Automatic Escaping

React escapes content in JSX by default:

```jsx
// Safe: React escapes userInput automatically
function UserName({ name }) {
  return <span>{name}</span>;
}

// Input: <script>alert('xss')</script>
// Output: &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;
```

### When React Escapes

- String interpolation in JSX: `<div>{content}</div>`
- Attribute values: `<div title={title}>`
- Property values: `<Component value={val} />`

### When React Does NOT Escape

- `dangerouslySetInnerHTML` — explicitly disabled
- `innerHTML` property assignment — forbidden in our codebase
- `eval()` — forbidden

---

## JavaScript Context

When embedding data in JavaScript, use JSON serialization:

```jsx
// Safe: Use JSON.stringify
const userData = JSON.parse('{"name": "John", "role": "admin"}');

// Never interpolate directly into script tags
// Anti-pattern:
// <script>var name = "{userInput}";</script>
```

### Server-Side Template Data

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import json

@app.get("/page", response_class=HTMLResponse)
async def get_page():
    # Pass data via data attribute, not inline script
    return """
    <!DOCTYPE html>
    <div id="app" data-user='{json.dumps(user_data)}'></div>
    <script>
      const userData = JSON.parse(
        document.getElementById('app').dataset.user
      );
    </script>
    """
```

---

## URL Context

URL-encode data in URL components:

```python
from urllib.parse import quote, quote_plus

# Path segment
safe_path = quote(untrusted_input)  # Encodes /, ?, &, =

# Query parameter
safe_query = quote_plus(untrusted_input)  # Encodes spaces as +

# URL construction
from urllib.parse import urljoin, urlunparse
safe_url = urlunparse((
    "https",           # scheme
    "api.example.com", # netloc
    "/endpoint",       # path
    "",                # params
    f"param={safe_query}", # query
    ""                 # fragment
))
```

---

## SQL Context

Use parameterized queries — no encoding needed:

```python
# CORRECT - SQLAlchemy handles encoding
result = db.query(User).filter(User.email == email).first()

# CORRECT - Raw parameterized query
query = text("SELECT * FROM users WHERE email = :email")
result = db.execute(query, {"email": user_input})

# NEVER - String concatenation (SQL injection)
# query = f"SELECT * FROM users WHERE email = '{user_input}'"
```

See [SQL Injection](sql-injection.md) for details.

---

## Shell Context

Never pass user input to shell commands:

### Anti-pattern

```python
# NEVER - Command injection
import os
os.system(f"convert {filename} -resize 512x512 output.png")
```

### Correct Pattern

```python
# Use subprocess with list, no shell
import subprocess
subprocess.run([
    "convert",
    filename,  # Safe - passed as argument, not shell
    "-resize", "512x512",
    "output.png"
], shell=False)
```

---

## HTML Context

If you must render HTML (rare), sanitize it first:

```python
import DOMPurify

def sanitize_html(dirty: str) -> str:
    """Sanitize HTML to prevent XSS."""
    return DOMPurify.sanitize(dirty, {
        ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li'],
        ALLOWED_ATTR: ['class'],
        FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
        FORBID_ATTR: ['onerror', 'onload', 'onclick']
    })
```

---

## Output Encoding Checklist

| Context | Method | Example |
|---|---|---|
| HTML | React escaping (default) | `<div>{data}</div>` |
| HTML attribute | React escaping | `<div title={data}>` |
| JavaScript | JSON.stringify | `const data = JSON.parse(json)` |
| URL path | urllib.quote | `quote(path)` |
| URL query | urllib.quote_plus | `quote_plus(query)` |
| SQL | Parameterized query | `db.query().filter(col == val)` |
| Shell | subprocess list | `subprocess.run([cmd, arg])` |
| CSS | Strict validation | Only allow-listed values |
| JSON | Pydantic serialization | `json.dumps(data)` |

---

## Testing Output Encoding

```python
import pytest

def test_xss_payload_encoded():
    """Verify XSS payloads are encoded in HTML."""
    payload = "<script>alert('xss')</script>"
    # Render in React (simulated)
    result = render_to_string("<div>{payload}</div>")

    assert "<script>" not in result
    assert "&lt;script&gt;" in result

def test_url_special_chars_encoded():
    """Verify URL special characters are encoded."""
    from urllib.parse import quote

    unsafe = "hello world?foo=bar&baz=qux"
    safe = quote(unsafe)

    assert " " not in safe
    assert "%20" in safe
    assert "?" not in safe or "%3F" in safe
```

---

## Cross-Reference

- [XSS](xss.md) — XSS prevention
- [SQL Injection](sql-injection.md) — SQL safety
- [Input Validation](input-validation.md) — Input gates
