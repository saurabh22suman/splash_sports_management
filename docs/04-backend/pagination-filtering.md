# Pagination, Filtering & Sorting

> This document covers cursor pagination, filter query parameters, sorting, and limit handling.

## Overview

We use **cursor-based pagination** for production scalability. Cursor pagination is more efficient than offset pagination when dealing with large datasets and real-time data.

## Cursor Pagination

### Why Cursor > Offset

| Aspect | Cursor | Offset |
|--------|--------|--------|
| Performance | O(1) | O(n) |
| Consistency | Stable under inserts | Skips/duplicates |
| Large pages | Fast at any position | Slow for high offsets |
| URL size | Small cursor | Large offset |

### Implementation

```python
# src/common/pagination.py
from typing import TypeVar, Generic, Optional, List
from pydantic import BaseModel, Field
import base64
import json


T = TypeVar("T")


class PageInfo(BaseModel):
    """Pagination metadata."""
    has_next: bool
    has_previous: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None
    total_count: Optional[int] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    page_info: PageInfo

    @classmethod
    def create(
        cls,
        items: List[T],
        limit: int,
        cursor: Optional[str] = None,
        total_count: Optional[int] = None,
    ) -> "PaginatedResponse[T]":
        has_next = len(items) > limit
        actual_items = items[:limit]

        return cls(
            items=actual_items,
            page_info=PageInfo(
                has_next=has_next,
                has_previous=cursor is not None,
                start_cursor=encode_cursor(items[0]) if items else None,
                end_cursor=encode_cursor(items[-1]) if items else None,
                total_count=total_count,
            ),
        )


def encode_cursor(item) -> str:
    """Encode item's sort keys as cursor."""
    cursor_data = {
        "id": str(item.id),
        "created_at": item.created_at.isoformat(),
    }
    return base64.urlsafe_b64encode(json.dumps(cursor_data).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    """Decode cursor to sort keys."""
    data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    return data
```

### Repository Implementation

```python
# src/booking/infrastructure/repositories.py
from uuid import UUID
from datetime import datetime


class SQLAlchemyBookingRepository:
    def list_paginated(
        self,
        customer_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[List[Booking], Optional[str]]:
        query = self._session.query(BookingModel).filter(
            BookingModel.customer_id == customer_id,
            BookingModel.deleted_at.is_(None)
        )

        # Apply cursor
        if cursor:
            cursor_data = decode_cursor(cursor)
            cursor_id = cursor_data.get("id")
            cursor_created_at = datetime.fromisoformat(cursor_data.get("created_at"))

            if sort_order == "desc":
                query = query.filter(
                    (BookingModel.created_at < cursor_created_at) |
                    (
                        BookingModel.created_at == cursor_created_at &
                        BookingModel.id < cursor_id
                    )
                )
            else:
                query = query.filter(
                    (BookingModel.created_at > cursor_created_at) |
                    (
                        BookingModel.created_at == cursor_created_at &
                        BookingModel.id > cursor_id
                    )
                )

        # Apply sorting
        sort_column = getattr(BookingModel, sort_by, BookingModel.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc(), BookingModel.id.desc())
        else:
            query = query.order_by(sort_column.asc(), BookingModel.id.asc())

        # Fetch one extra to determine if there's more
        items = query.limit(limit + 1).all()

        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = encode_cursor(items[-1])

        return items, next_cursor
```

### API Endpoint

```python
# src/booking/interfaces/router.py
from fastapi import Query, Depends
from typing import Optional


@router.get("/bookings", response_model=PaginatedResponse[BookingOut])
async def list_bookings(
    customer_id: Optional[UUID] = None,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|date)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    service: BookingService = Depends(get_booking_service),
):
    result = service.list_bookings(
        customer_id=customer_id,
        limit=limit,
        cursor=cursor,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return result
```

## Filtering

### Query Parameter Patterns

```python
# Filter by exact match
GET /bookings?status=confirmed

# Filter by multiple values (IN)
GET /bookings?status=pending,confirmed

# Filter by range (gt, gte, lt, lte)
GET /bookings?date_from=2024-01-01&date_to=2024-01-31

# Filter by relationship
GET /bookings?customer_id=abc-123
GET /bookings?facility_id=xyz-456
```

### Filter Implementation

```python
# src/booking/application/queries.py
from dataclasses import dataclass
from uuid import UUID
from datetime import date
from typing import Optional
from enum import Enum

from booking.domain.value_objects import BookingStatus


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class BookingQuery:
    """Query parameters for booking list."""
    customer_id: Optional[UUID] = None
    facility_id: Optional[UUID] = None
    status: Optional[list[str]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    search: Optional[str] = None

    def apply(self, query):
        """Apply filters to SQLAlchemy query."""
        if self.customer_id:
            query = query.filter(BookingModel.customer_id == self.customer_id)

        if self.facility_id:
            query = query.filter(BookingModel.facility_id == self.facility_id)

        if self.status:
            statuses = [s.value if isinstance(s, BookingStatus) else s for s in self.status]
            query = query.filter(BookingModel.status.in_(statuses))

        if self.date_from:
            query = query.filter(BookingModel.slot_date >= self.date_from)

        if self.date_to:
            query = query.filter(BookingModel.slot_date <= self.date_to)

        if self.search:
            query = query.filter(
                or_(
                    BookingModel.notes.ilike(f"%{self.search}%"),
                )
            )

        return query
```

## Sorting

### Sort Parameter Format

```
GET /bookings?sort=created_at,-date
```

- Prefix with `-` for descending
- Default is ascending

```python
# Sort parsing
def parse_sort_param(sort: str) -> list[tuple[str, str]]:
    """Parse sort parameter into (field, order) tuples."""
    if not sort:
        return [("created_at", "desc")]

    result = []
    for part in sort.split(","):
        part = part.strip()
        if part.startswith("-"):
            result.append((part[1:], "desc"))
        else:
            result.append((part, "asc"))

    return result
```

### Default Sort

> **Rule** — Default sort must be deterministic (include `id` as tiebreaker).

```python
# Default: created_at DESC, id DESC
# This ensures consistent ordering even for same-timestamp items
query = query.order_by(
    BookingModel.created_at.desc(),
    BookingModel.id.desc()
)
```

## Request/Response Examples

### Request

```
GET /v1/bookings?limit=20&cursor=eyJpZCI6IjEyMzQ1Njc4OTAxMjM0NTYiLCJjcmVhdGVkX2F0IjoiMjAyNC0wMS0xNVQxMDozMDowMFoifQ==&sort=-created_at,date&status=pending,confirmed&facility_id=abc-123
```

### Response

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "customer_id": "660e8400-e29b-41d4-a716-446655440001",
      "facility_id": "abc-123",
      "date": "2024-01-15",
      "start_time": "10:00",
      "end_time": "11:00",
      "status": "confirmed",
      "created_at": "2024-01-10T10:30:00Z",
      "updated_at": "2024-01-10T10:30:00Z"
    }
  ],
  "page_info": {
    "has_next": true,
    "has_previous": true,
    "start_cursor": "eyJpZCI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsImNyZWF0ZWRfYXQiOiIyMDI0LTAxLTE1VDEwOjMwOjAwWiJ9",
    "end_cursor": "eyJpZCI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsImNyZWF0ZWRfYXQiOiIyMDI0LTAxLTE1VDEwOjMwOjAwWiJ9",
    "total_count": 1523
  }
}
```

## Anti-Patterns

1. **Offset pagination** — Slow for large offsets, inconsistent under inserts
2. **No default limits** — Allows unbounded queries
3. **Missing max limit** — Allows DoS via huge page requests
4. **Non-deterministic sort** — Sort without tiebreaker causes inconsistency

## Related Documents

- [API Pagination](../08-apis/pagination.md)
- [Filtering & Search](../08-apis/filtering-search.md)
- [Repositories](repositories.md)
