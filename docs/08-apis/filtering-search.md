# Filtering, Search & Sorting

> This document covers query parameter patterns for filtering, search, and sorting.

## Overview

We use explicit query parameters for filtering and sorting. Search is a separate endpoint for full-text search.

## Filter Parameters

### Simple Filters

```
GET /v1/bookings?status=confirmed
GET /v1/bookings?customer_id=uuid
GET /v1/bookings?facility_id=uuid
```

### Multiple Values (IN)

```
GET /v1/bookings?status=pending,confirmed
```

### Range Filters

```
GET /v1/bookings?date_from=2024-01-01
GET /v1/bookings?date_to=2024-01-31
GET /v1/bookings?date_from=2024-01-01&date_to=2024-01-31
```

### Combining Filters

```
GET /v1/bookings?status=pending,confirmed&facility_id=uuid&date_from=2024-01-01
```

## Sort Parameters

```
GET /v1/bookings?sort=created_at
GET /v1/bookings?sort=-created_at    # descending
GET /v1/bookings?sort=-created_at,date  # multiple
```

| Prefix | Meaning |
|--------|---------|
| (none) | Ascending |
| `-` | Descending |

## Filter Operators

| Operator | Parameter | Example |
|----------|-----------|---------|
| Equals | `field=value` | `status=pending` |
| In | `field=a,b,c` | `status=pending,confirmed` |
| Greater than | `field_gt=value` | `created_at_gt=2024-01-01` |
| Greater or equal | `field_gte=value` | `created_at_gte=2024-01-01` |
| Less than | `field_lt=value` | `date_lt=2024-01-31` |
| Less or equal | `field_lte=value` | `date_lte=2024-01-31` |

## Implementation

### Query Parser

```python
# src/common/filters.py
from dataclasses import dataclass
from typing import Optional
from datetime import date
from enum import Enum


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class BookingFilters:
    """Booking filter parameters."""
    status: Optional[list[str]] = None
    customer_id: Optional[str] = None
    facility_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    sort: Optional[str] = "created_at"

    @classmethod
    def from_query_params(cls, params: dict) -> "BookingFilters":
        """Parse query parameters into filters."""
        # Handle comma-separated values
        status = params.get("status")
        if status:
            status = status.split(",")

        return cls(
            status=status,
            customer_id=params.get("customer_id"),
            facility_id=params.get("facility_id"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            sort=params.get("sort", "created_at"),
        )
```

### Apply to Query

```python
class SQLAlchemyBookingRepository:
    def apply_filters(self, query, filters: BookingFilters):
        """Apply filters to query."""
        if filters.status:
            query = query.filter(BookingModel.status.in_(filters.status))

        if filters.customer_id:
            query = query.filter(BookingModel.customer_id == filters.customer_id)

        if filters.facility_id:
            query = query.filter(BookingModel.facility_id == filters.facility_id)

        if filters.date_from:
            query = query.filter(BookingModel.slot_date >= filters.date_from)

        if filters.date_to:
            query = query.filter(BookingModel.slot_date <= filters.date_to)

        # Apply sorting
        query = self._apply_sort(query, filters.sort)

        return query

    def _apply_sort(self, query, sort_param: str):
        """Apply sorting to query."""
        parts = sort_param.split(",")

        for part in parts:
            part = part.strip()
            if part.startswith("-"):
                column = getattr(BookingModel, part[1:], BookingModel.created_at)
                query = query.order_by(column.desc())
            else:
                column = getattr(BookingModel, part, BookingModel.created_at)
                query = query.order_by(column.asc())

        return query
```

## Search

Search is a separate endpoint for full-text search:

```
GET /v1/bookings/search?q=tennis
```

```python
@router.get("/bookings/search")
async def search_bookings(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    service: BookingService = Depends(get_booking_service),
):
    results = service.search_bookings(query=q, limit=limit)
    return results
```

## Examples

### List pending bookings for a facility

```
GET /v1/bookings?status=pending&facility_id=facility-uuid&sort=-created_at
```

### Bookings in date range

```
GET /v1/bookings?date_from=2024-01-01&date_to=2024-01-31&sort=date
```

### Complex query

```
GET /v1/bookings?status=pending,confirmed&facility_id=facility-uuid&date_from=2024-01-01&sort=-created_at,date&limit=50
```

## Anti-Patterns

1. **Filter in request body** — Use query parameters
2. **Search in list endpoint** — Use separate search endpoint
3. **No default sort** — Results are unpredictable
4. **Complex filter syntax** — Keep filters simple

## Related Documents

- [Pagination](pagination.md)
- [REST Design](rest-design.md)
