# Redis

> Data structures: Strings, Hashes, Sorted Sets, Streams, HyperLogLog. Lua scripts for atomic ops. Eviction policy: allkeys-lru. Memory budget. Anti-patterns.

This document establishes Redis usage patterns for the Splashh Sports Platform. Redis serves as our cache, session store, message broker, and rate limiter.

---

## Data Structures We Use

### Strings

Simple key-value storage:

```python
# Session storage
await redis.setex(
    f"session:{user_id}",
    3600,  # 1 hour TTL
    json.dumps(session_data)
)

# Counters
await redis.incr(f"rate_limit:{ip_address}")
await redis.incrby(f"daily_bookings:{tenant_id}", 1)

# Locking
await redis.set("lock:booking:123", "1", nx=True, ex=10)  # 10 second lock
```

### Hashes

Structured data:

```python
# User session data
await redis.hset(
    "session:user:123",
    mapping={
        "user_id": "123",
        "tenant_id": "tenant-abc",
        "roles": json.dumps(["member"]),
        "created_at": "2024-01-15T10:00:00Z"
    }
)

# Get all session data
session = await redis.hgetall("session:user:123")

# Update single field
await redis.hset("session:user:123", "last_activity", datetime.utcnow().isoformat())
```

### Sorted Sets

Leaderboards, time-series:

```python
# Booking count by day (for analytics)
await redis.zadd(
    "bookings:daily:2024-01",
    {
        "2024-01-15": 42,
        "2024-01-16": 38,
    }
)

# Get top 10 booking days
top_days = await redis.zrevrange("bookings:daily:2024-01", 0, 9, withscores=True)

# Get rank for specific day
rank = await redis.zrevrank("bookings:daily:2024-01", "2024-01-15")
```

### Streams

Event bus, message queues:

```python
# Event publishing
await redis.xadd(
    "events:booking",
    {
        "type": "BookingCreated",
        "booking_id": "123",
        "tenant_id": "tenant-abc",
        "user_id": "456"
    },
    maxlen=10000  # Limit stream length
)

# Consumer group for workers
await redis.xgroup_create(
    "events:booking",
    "booking-workers",
    id="0",  # Start from beginning
    mkstream=True
)

# Read messages
messages = await redis.xreadgroup(
    "booking-workers",
    "worker-1",
    {"events:booking": ">"},
    count=10,
    block=5000  # 5 second timeout
)
```

### HyperLogLog

Unique counts:

```python
# Daily active users
await redis.pfadd(f"dau:{date}", *user_ids)
unique_count = await redis.pfcount(f"dau:{date}")

# Merge for period
await redis.pfmerge("dau:week", f"dau:2024-01-15", f"dau:2024-01-16")
```

---

## Lua Scripts for Atomic Operations

```python
# Lua scripts for atomic operations

# Atomic counter with rate limiting
RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = tonumber(redis.call('GET', key) or '0')
if current >= limit then
    return 0
end

redis.call('INCR', key)
redis.call('EXPIRE', key, window)
return current + 1
"""

# Atomic booking slot reservation
BOOKING_RESERVE_SCRIPT = """
local slot_key = KEYS[1]
local booking_key = KEYS[2]
local slot_id = ARGV[1]
local booking_id = ARGV[2]
local ttl = tonumber(ARGV[3])

-- Check if slot is available
local existing = redis.call('GET', slot_key)
if existing then
    return 0
end

-- Reserve the slot
redis.call('SET', slot_key, booking_id, 'EX', ttl)
redis.call('HSET', booking_key, 'slot_id', slot_id)
return 1
"""


class LuaScripts:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Returns True if request is allowed."""
        result = await self.redis.eval(
            RATE_LIMIT_SCRIPT,
            1,  # Number of keys
            key,
            limit,
            window
        )
        return result == 1

    async def reserve_slot(self, slot_id: str, booking_id: str, ttl: int = 600) -> bool:
        """Atomically reserve a booking slot."""
        result = await self.redis.eval(
            BOOKING_RESERVE_SCRIPT,
            2,  # Number of keys
            f"slot:{slot_id}",
            f"booking:{booking_id}",
            slot_id,
            booking_id,
            ttl
        )
        return result == 1
```

---

## Eviction Policy

```python
# redis.conf configuration
maxmemory 2gb                    # 2GB memory limit
maxmemory-policy allkeys-lru     # Evict least recently used keys
maxmemory-samples 5              # Sample 5 keys for eviction
```

> **Rule** — Use `allkeys-lru` for general caching. This ensures frequently accessed data stays in cache.

---

## Memory Budget

| Use Case | Estimated Memory | Keys |
|----------|-----------------|------|
| Session storage | 500MB | ~50K sessions |
| API cache | 1GB | ~100K entries |
| Rate limiting | 100MB | ~10K counters |
| Streams | 200MB | ~20K events |
| Other | 200MB | Various |
| **Total** | **2GB** | |

> **Guideline** — Monitor memory with `redis-cli INFO memory` and set alerts at 80% capacity.

---

## Anti-Patterns to Avoid

### 1. KEYS in Production

```python
# Anti-pattern - NEVER use KEYS in production
keys = await redis.keys("booking:*")  # Blocks Redis!

# Use SCAN instead
async for key in redis.scan_iter(match="booking:*"):
    process(key)
```

### 2. Oversized Values

```python
# Anti-pattern - storing large objects
await redis.set("huge_data", json.dumps(megabytes_of_data))

# Better: Store reference, keep data elsewhere
await redis.set("data_ref:123", json.dumps({
    "location": "s3://bucket/data-123.json",
    "checksum": "abc123"
}))
```

### 3. No TTL on Cache Keys

```python
# Anti-pattern - no expiration
await redis.set("cache:data", value)  # Stays forever!

# Always set TTL
await redis.setex("cache:data", 300, value)  # 5 min TTL
```

### 4. Using Redis for Everything

```python
# Anti-pattern - using Redis for data that belongs in DB
await redis.set("user:123:profile", user_profile)  # Should be in PostgreSQL

# Redis is for: cache, sessions, pub/sub, rate limiting
# PostgreSQL is for: persistent data
```

---

## Connection Management

```python
# apps/backend/src/common/redis.py
import redis.asyncio as redis
from config import settings

class RedisPool:
    _pool: redis.ConnectionPool = None

    @classmethod
    async def get_pool(cls) -> redis.ConnectionPool:
        if cls._pool is None:
            cls._pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                max_connections=50,
                decode_responses=True,
            )
        return cls._pool

    @classmethod
    async def get_client(cls) -> redis.Redis:
        pool = await cls.get_pool()
        return redis.Redis(connection_pool=pool)
```

---

## Trade-offs

| Data Structure | Best For | Avoid When |
|---------------|----------|-----------|
| String | Sessions, counters, locks | Structured data |
| Hash | Objects, session data | Arrays, time series |
| Sorted Set | Leaderboards, rankings | Simple lookups |
| Stream | Event bus, job queues | Request/response |
| HyperLogLog | Unique counts | Exact counts needed |

---

## Related Documents

- [Caching](caching.md) — Cache layer strategies
- [Queue Design](queue-design.md) — Redis Streams for queues
- [Async Processing](async-processing.md) — Background jobs with Redis
