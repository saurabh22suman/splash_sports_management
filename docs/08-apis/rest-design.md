# REST Design

> This document covers REST API design principles, resource modeling, URL conventions, and response patterns.

## Overview

We follow REST conventions with pragmatic deviations. URLs model resources, HTTP verbs express actions, and responses are consistent.

## Resource Modeling

### URL Structure

```
/v1/{collection}/{id}
```

| Pattern | Method | Use |
|---------|--------|-----|
| `/v1/bookings` | GET | List bookings |
| `/v1/bookings` | POST | Create booking |
| `/v1/bookings/{id}` | GET | Get booking |
| `/v1/bookings/{id}` | PUT/PATCH | Update booking |
| `/v1/bookings/{id}` | DELETE | Delete booking |

### Resource Naming

> **Rule** — Use plural nouns for collections.

```python
# Good
/v1/bookings
/v1/customers
/v1/facilities
/v1/memberships

# Bad
/v1/booking
/v1/getBookings
```

### Nested Resources

```python
# Good: Resource under another resource
GET /v1/customers/{customer_id}/bookings
GET /v1/facilities/{facility_id}/slots

# Bad: Too deep
GET /v1/customers/{customer_id}/bookings/{booking_id}/lines/{line_id}
```

## HTTP Methods

| Method | Idempotent | Use |
|--------|------------|-----|
| GET | Yes | Retrieve resources |
| POST | No | Create resources |
| PUT | Yes | Replace entire resource |
| PATCH | Yes | Partial update |
| DELETE | Yes | Delete resource |

### Examples

```python
# GET - Retrieve
GET /v1/bookings
GET /v1/bookings/{id}

# POST - Create
POST /v1/bookings
{
    "customer_id": "uuid",
    "facility_id": "uuid",
    "date": "2024-01-15",
    "start_time": "10:00",
    "end_time": "11:00"
}

# PUT - Replace entire resource
PUT /v1/bookings/{id}
{
    "customer_id": "uuid",
    "facility_id": "uuid",
    "date": "2024-01-15",
    "start_time": "10:00",
    "end_time": "11:00",
    "status": "confirmed"  # Required for PUT
}

# PATCH - Partial update
PATCH /v1/bookings/{id}
{
    "notes": "Golf clubs rented"
}

# DELETE - Delete
DELETE /v1/bookings/{id}
```

## URL Patterns

### Query Parameters

```python
# Filtering
GET /v1/bookings?status=confirmed
GET /v1/bookings?date_from=2024-01-01&date_to=2024-01-31
GET /v1/bookings?customer_id=uuid

# Pagination
GET /v1/bookings?limit=20&cursor=abc123

# Sorting
GET /v1/bookings?sort=-created_at,date

# Combined
GET /v1/bookings?status=pending&sort=-created_at&limit=10
```

### No Verbs in URLs

```python
# Bad
GET /v1/getBookings
POST /v1/createBooking
POST /v1/cancelBooking/{id}

# Good
POST /v1/bookings  # Create
DELETE /v1/bookings/{id}  # Cancel (soft delete)
PATCH /v1/bookings/{id}/cancel  # If needed, use PATCH for action
```

## Response Format

### Success Responses

```json
// Single resource - 200 OK
{
  "id": "booking-123",
  "customer_id": "customer-456",
  "facility_id": "facility-789",
  "date": "2024-01-15",
  "status": "confirmed"
}

// Collection - 200 OK
{
  "items": [...],
  "page_info": {
    "has_next": true,
    "next_cursor": "abc123"
  }
}

// Created - 201 Created
{
  "id": "booking-123",
  "created_at": "2024-01-15T10:30:00Z",
  ...
}
```

### Error Responses

```json
// 400 Bad Request
{
  "type": "https://api.splashh.com/errors/validation_error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Request validation failed",
  "errors": [
    {
      "field": "end_time",
      "message": "end_time must be after start_time"
    }
  ]
}

// 404 Not Found
{
  "type": "https://api.splashh.com/errors/not_found",
  "title": "NotFoundError",
  "status": 404,
  "detail": "Booking with ID booking-123 not found"
}
```

## Hypermedia (HATEOAS-Light)

We include basic links, but not full HATEOAS:

```json
{
  "id": "booking-123",
  "status": "confirmed",
  "links": {
    "self": "/v1/bookings/booking-123",
    "customer": "/v1/customers/customer-456",
    "facility": "/v1/facilities/facility-789"
  }
}
```

## Content Negotiation

```python
# Request
GET /v1/bookings/booking-123
Accept: application/json

# Response
Content-Type: application/json
```

## API Versioning in URL

```python
# All URLs include version
/v1/bookings
/v2/bookings

# Not in header (avoid)
Accept: application/vnd.splashh.v1+json
```

## Batch Operations

```python
# For multiple creates
POST /v1/bookings/batch
{
  "bookings": [
    {...},
    {...}
  ]
}

# Response
{
  "items": [...],
  "failed": [
    {"index": 1, "error": "Slot not available"}
  ]
}
```

## Anti-Patterns

1. **Verbs in URLs** — Use HTTP methods instead
2. **CamelCase** — Use snake_case
3. **Plural/singular inconsistency** — Always plural
4. **No pagination** — Allows unbounded responses

## Related Documents

- [Status Codes](status-codes.md)
- [Error Responses](error-responses.md)
- [Pagination](pagination.md)
- [Filtering & Search](filtering-search.md)
