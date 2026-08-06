# HTTP Status Codes

> This document provides a comprehensive table of when to use each HTTP status code.

## Overview

HTTP status codes communicate the result of a request. Using them correctly is critical for proper API semantics and client error handling.

## Status Code Reference

| Code | Name | When to Use |
|------|------|-------------|
| **2xx Success** | | |
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST that creates resource |
| 202 | Accepted | Async operation accepted, processing |
| 204 | No Content | Successful DELETE, no response body |
| **4xx Client Errors** | | |
| 400 | Bad Request | Invalid request syntax, validation error |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 405 | Method Not Allowed | HTTP method not supported |
| 409 | Conflict | State conflict (e.g., duplicate) |
| 410 | Gone | Resource was removed (deprecated) |
| 422 | Unprocessable Entity | Business rule violation |
| 429 | Too Many Requests | Rate limit exceeded |
| **5xx Server Errors** | | |
| 500 | Internal Server Error | Unexpected server error |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Temporary overload/maintenance |
| 504 | Gateway Timeout | Upstream timeout |

## Detailed Usage

### 200 OK

```python
# GET successful
GET /v1/bookings/booking-123

# PUT/PATCH successful update
PUT /v1/bookings/booking-123
{"notes": "Updated notes"}
# Response: 200 OK with updated resource
```

### 201 Created

```python
# POST to create resource
POST /v1/bookings
{"customer_id": "uuid", ...}

# Response
201 Created
Location: /v1/bookings/booking-123
{"id": "booking-123", ...}
```

### 202 Accepted

```python
# Async operation accepted
POST /v1/bookings/bulk
{"bookings": [...]}

# Response - will process async
202 Accepted
{
  "job_id": "job-123",
  "status": "processing",
  "status_url": "/v1/jobs/job-123"
}
```

### 204 No Content

```python
# DELETE successful
DELETE /v1/bookings/booking-123

# Response: 204 No Content (no body)
```

### 400 Bad Request

```python
# Invalid JSON
POST /v1/bookings
"not valid json"

# Validation error
POST /v1/bookings
{"date": "invalid-date"}

# Response
400 Bad Request
{"type": "...", "title": "Validation Error", "status": 400, ...}
```

### 401 Unauthorized

```python
# No token
GET /v1/bookings

# Response
401 Unauthorized
{"type": "...", "title": "AuthenticationError", "status": 401}

# Invalid/expired token
401 Unauthorized
{"type": "...", "title": "AuthenticationError", "status": 401, "detail": "Token expired"}
```

### 403 Forbidden

```python
# Authenticated but no permission
GET /v1/admin/users

# Response
403 Forbidden
{"type": "...", "title": "AuthorizationError", "status": 403}
```

### 404 Not Found

```python
# Resource doesn't exist
GET /v1/bookings/nonexistent-id

# Response
404 Not Found
{"type": "...", "title": "NotFoundError", "status": 404}
```

### 409 Conflict

```python
# Duplicate resource
POST /v1/customers
{"email": "exists@example.com"}

# Slot already booked
POST /v1/bookings
{"slot": "already-taken"}

# Response
409 Conflict
{"type": "...", "title": "ConflictError", "status": 409}
```

### 410 Gone

```python
# Deprecated endpoint
GET /v1/bookings/old-id

# Response
410 Gone
{"type": "...", "title": "Gone", "status": 410, "sunset": "2024-07-01"}
```

### 422 Unprocessable Entity

```python
# Business rule violation
POST /v1/bookings
{"date": "2020-01-01"}  # Past date not allowed

# Response
422 Unprocessable Entity
{"type": "...", "title": "BusinessRuleError", "status": 422}
```

### 429 Too Many Requests

```python
# Rate limit exceeded

# Response
429 Too Many Requests
Retry-After: 60
{"type": "...", "title": "RateLimitError", "status": 429, "retry_after": 60}
```

### 500 Internal Server Error

```python
# Unexpected error

# Response (don't leak internals)
500 Internal Server Error
{"type": "...", "title": "InternalError", "status": 500, "request_id": "abc-123"}
```

### 503 Service Unavailable

```python
# Maintenance or overload

# Response
503 Service Unavailable
Retry-After: 300
{"type": "...", "title": "ServiceUnavailable", "status": 503}
```

## Decision Tree

```
Request received
       |
       v
Authentication valid?
   |         \
   No        Yes
   |          |
  401      Authorized?
       |         \
       No        Yes
       |          |
      403     Request valid?
           |         \
           No        Yes
           |          |
          400     Resource exists?
              |         \
              No        Yes
              |          |
             404     Business valid?
                  |         \
                  No        Yes
                  |          |
                422     Action success?
                     |         \
                     No        Yes
                     |          |
                   409      Status?
                          /   |   \
                        200   201   204
```

## Anti-Patterns

1. **200 for errors** — Always use appropriate error codes
2. **404 for authorization** — Use 403 instead
3. **500 for everything** — Map to specific error codes
4. **Leaking internals** — Don't expose stack traces

## Related Documents

- [REST Design](rest-design.md)
- [Error Responses](error-responses.md)
- [Rate Limiting](rate-limiting.md)
