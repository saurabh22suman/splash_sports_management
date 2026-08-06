# Pagination

> This document covers cursor-based pagination, response format, and why cursor > offset.

## Overview

We use **cursor pagination** for production scalability. Cursor pagination is more performant than offset pagination for large datasets.

## Why Cursor > Offset

| Aspect | Cursor | Offset |
|--------|--------|--------|
| Performance | O(1) | O(n) |
| Consistency | Stable | Skips/duplicates |
| Large pages | Fast anywhere | Slow for high offsets |
| URL length | Short | Gets long |

## Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Items per page (max 100) |
| `cursor` | string | null | Pagination cursor |

```
GET /v1/bookings?limit=20&cursor=eyJpZCI6IjEyMzQ1Njc4OTAxMjM0NTYifQ==
```

## Response Format

```json
{
  "items": [
    {
      "id": "booking-123",
      "customer_id": "customer-456",
      "date": "2024-01-15",
      "status": "confirmed"
    }
  ],
  "page_info": {
    "has_next": true,
    "has_previous": false,
    "start_cursor": "eyJpZCI6IjEyMzQ1Njc4OTAxMjM0NTYifQ==",
    "end_cursor": "eyJpZCI6IjxhYmNkZWYifQ=="
  }
}
```

## Implementation

### Response Schema

```python
# src/common/pagination.py
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel


T = TypeVar("T")


class PageInfo(BaseModel):
    """Pagination metadata."""
    has_next: bool
    has_previous: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    page_info: PageInfo
```

### Encoding Cursors

```python
import base64
import json
from datetime import datetime
from uuid import UUID


def encode_cursor(sort_value, id_value) -> str:
    """Encode sort key + id as cursor."""
    cursor_data = {
        "sort": sort_value,
        "id": str(id_value),
    }
    return base64.urlsafe_b64encode(json.dumps(cursor_data).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    """Decode cursor to sort keys."""
    data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    return data
```

### Repository Query

```python
# src/booking/infrastructure/repositories.py
class SQLAlchemyBookingRepository:
    def list_paginated(
        self,
        tenant_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> tuple[List[Booking], Optional[str]]:
        query = self._session.query(BookingModel).filter(
            BookingModel.tenant_id == tenant_id,
            BookingModel.deleted_at.is_(None)
        )

        # Apply cursor
        if cursor:
            cursor_data = decode_cursor(cursor)
            cursor_sort = cursor_data["sort"]
            cursor_id = cursor_data["id"]

            query = query.filter(
                (BookingModel.created_at < cursor_sort) |
                (
                    BookingModel.created_at == cursor_sort &
                    BookingModel.id < cursor_id
                )
            )

        # Sort by created_at DESC, id DESC
        query = query.order_by(
            BookingModel.created_at.desc(),
            BookingModel.id.desc()
        )

        # Fetch one extra to check for next page
        results = query.limit(limit + 1).all()

        next_cursor = None
        if len(results) > limit:
            results = results[:limit]
            last_item = results[-1]
            next_cursor = encode_cursor(last_item.created_at, last_item.id)

        return results, next_cursor
```

### API Endpoint

```python
# src/booking/router.py
from fastapi import Query, Depends


@router.get("/bookings", response_model=PaginatedResponse[BookingOut])
async def list_bookings(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    service: BookingService = Depends(get_booking_service),
):
    result = service.list_bookings(limit=limit, cursor=cursor)
    return result
```

## Client Usage

```python
// First request
response = await fetch("/v1/bookings?limit=20");
data = await response.json();

// Get next page
if (data.page_info.has_next) {
  response = await fetch(`/v1/bookings?limit=20&cursor=${data.page_info.end_cursor}`);
}

// Get previous page
if (data.page_info.has_previous) {
  response = await fetch(`/v1/bookings?limit=20&cursor=${data.page_info.start_cursor}`);
}
```

## Anti-Patterns

1. **Offset pagination** — Slow for large datasets
2. **No max limit** — Can request millions of rows
3. **Non-deterministic cursors** — Sort must include unique field (id)
4. **No cursor** — First page has no starting point

## Related Documents

- [Backend Pagination](../04-backend/pagination-filtering.md)
- [Filtering & Search](filtering-search.md)
