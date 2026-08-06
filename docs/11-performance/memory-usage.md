# Memory Usage

> Memory profiling tools. Leak detection. Worker memory limits. Container memory limits.

This document establishes memory management practices for the Splashh Sports Platform. We monitor and optimize memory usage to prevent OOM (out of memory) crashes.

---

## Memory Profiling

### Python tracemalloc

```python
# apps/backend/src/common/profiling/memory.py
import tracemalloc
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def profile_memory(operation: str):
    """Profile memory usage of an operation."""
    tracemalloc.start()

    snapshot_before = tracemalloc.take_snapshot()

    yield

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Calculate difference
    top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')

    logger.info(
        f"Memory profile: {operation}",
        extra={
            "operation": operation,
            "top_allocations": [
                {
                    "file": str(stat.traceback),
                    "size_diff": stat.size_diff,
                    "count_diff": stat.count_diff,
                }
                for stat in top_stats[:10]
            ]
        }
    )


# Usage
async def generate_report():
    with profile_memory("generate_report"):
        # Operation to profile
        data = await fetch_report_data()
        result = process_data(data)
        return result
```

### py-spy

```bash
# Profile running process
py-spy record -o profile.svg -- python -m uvicorn main:app

# Profile with flamegraph
py-spy record -o profile.html -- python -m uvicorn main:app
```

---

## Leak Detection

### Common Memory Leaks

```python
# Anti-pattern 1: Global state accumulation
class Cache:
    _cache = {}  # Never cleared!

    @classmethod
    def set(cls, key, value):
        cls._cache[key] = value  # Grows unbounded!


# Anti-pattern 2: Event listener accumulation
class EventEmitter:
    def __init__(self):
        self._listeners = []

    def on(self, event, callback):
        self._listeners.append((event, callback))  # Never removed!

    def off(self, event, callback):
        # Bug: This doesn't actually remove listeners properly
        pass


# Anti-pattern 3: Circular references
class Node:
    def __init__(self):
        self.parent = None
        self.children = []

    def add_child(self, child):
        self.children.append(child)
        child.parent = self  # Circular reference
```

### Detection Strategy

```python
# apps/backend/src/common/monitoring/memory.py
import psutil
import asyncio
from datetime import datetime

class MemoryMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = None

    async def start(self):
        """Start monitoring."""
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        logger.info(f"Baseline memory: {self.baseline_memory} MB")

        # Schedule periodic checks
        while True:
            await asyncio.sleep(60)
            await self.check_memory()

    async def check_memory(self):
        """Check for memory leaks."""
        current = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = current - self.baseline_memory

        # Alert if memory grew significantly
        if memory_growth > 100:  # 100MB growth
            logger.warning(
                "Memory leak detected",
                extra={
                    "baseline": self.baseline_memory,
                    "current": current,
                    "growth": memory_growth,
                }
            )

        # Log current usage
        logger.info(
            "Memory usage",
            extra={
                "rss_mb": round(current, 2),
                "vms_mb": round(self.process.memory_info().vms / 1024 / 1024, 2),
            }
        )
```

---

## Worker Memory Limits

### Celery Workers

```python
# celery_config.py
# Memory limit per worker
worker_max_memory_per_child = 524288  # 512MB

# Kill worker if memory exceeds limit
worker_max_tasks_per_child = 1000  # Restart after N tasks
```

### Gunicorn Workers

```bash
# gunicorn.conf.py
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_tmp_dir = "/dev/shm"

# Memory limits (via systemd)
# MemoryMax=2G in systemd service
```

---

## Container Memory Limits

### Kubernetes

```yaml
# deployment.yaml
spec:
  containers:
    - name: api
      image: splashh/api:latest
      resources:
        requests:
          memory: "512Mi"
          cpu: "250m"
        limits:
          memory: "1Gi"
          cpu: "1000m"
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  api:
    image: splashh/api:latest
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

---

## Memory Optimization

### 1. Use Generators

```python
# Bad: Load all into memory
def get_all_bookings():
    bookings = await db.query(Booking).all()
    return [b.to_dict() for b in bookings]

# Good: Stream results
async def get_all_bookings():
    """Stream bookings one at a time."""
    result = await db.stream_scalars(
        select(Booking)
    )

    async for booking in result:
        yield booking.to_dict()
```

### 2. Pagination

```python
# Always paginate large results
async def get_bookings(limit: int = 100, offset: int = 0):
    return await db.query(Booking).limit(limit).offset(offset)
```

### 3. Release Resources

```python
# Always close resources
async def process_large_file():
    file = await storage.download("large-file")

    try:
        async for chunk in file:
            process(chunk)
    finally:
        await file.close()  # Release memory
```

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| Generators | Lower memory | More complex code |
| Pagination | Predictable memory | More DB round trips |
| Strict limits | Predictable costs | Potential OOM kills |

---

## Related Documents

- [Observability](observability.md) — Memory metrics
- [Async Processing](async-processing.md) — Worker processes
- [Performance Budgets](performance-budgets.md) — Memory budgets in CI
