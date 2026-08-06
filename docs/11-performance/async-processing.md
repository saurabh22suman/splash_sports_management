# Async Processing

> When to async: emails, SMS, webhooks, reports, image processing. When NOT to async: payment authorization. Job design. Idempotency.

This document establishes when and how to use async processing in the Splashh Sports Platform. Not everything needs to be async, but certain operations benefit greatly from background processing.

---

## When to Use Async Processing

| Operation | Recommended | Reason |
|-----------|-------------|--------|
| Email notifications | Async | Not time-critical, can retry |
| SMS notifications | Async | Third-party API, can retry |
| Webhook delivery | Async | External system, retry on failure |
| Report generation | Async | CPU intensive, takes time |
| Image processing | Async | CPU intensive |
| Analytics aggregation | Async | Can be scheduled |
| Cache warming | Async | Background task |
| Data export | Async | Can take minutes |

### When NOT to Use Async

| Operation | Reason |
|-----------|--------|
| Payment authorization | Must be immediate, critical |
| Booking confirmation | User waiting for result |
| Login/authentication | User waiting for response |
| Data validation | User waiting for feedback |

---

## Job Design Principles

### 1. Idempotency

Jobs must be safe to run multiple times:

```python
# Bad: Not idempotent
async def send_welcome_email(user_id: str):
    user = await get_user(user_id)
    await send_email(user.email, "Welcome!")  # Sends duplicate if retried!

# Good: Idempotent
async def send_welcome_email(job: Job):
    user_id = job.payload["user_id"]
    user = await get_user(user_id)

    # Check if already sent
    if user.welcome_email_sent:
        return  # Skip if already sent

    await send_email(user.email, "Welcome!")
    await mark_email_sent(user_id)
```

### 2. Retriable

Jobs should handle transient failures:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
async def send_sms(phone: str, message: str):
    # External API call
    result = await sms_client.send(phone, message)
    if result.error:
        raise RetryError(result.error)
    return result
```

### 3. Payload Self-Contained

Include all needed data in the job, not references:

```python
# Bad: Reference to data that might change
async def process_booking(job: Job):
    booking_id = job.payload["booking_id"]
    booking = await get_booking(booking_id)  # Might change by retry time!

# Good: Include data in payload
async def process_booking(job: Job):
    booking_data = job.payload["booking"]  # Snapshot at creation time
    await process_booking_data(booking_data)
```

---

## Background Job Implementation

```python
# apps/backend/src/common/jobs/base.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from enum import Enum
import json
import hashlib

class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class Job(ABC):
    def __init__(self, payload: dict[str, Any]):
        self.id = self._generate_id(payload)
        self.payload = payload
        self.status = JobStatus.PENDING
        self.attempts = 0
        self.max_attempts = 3
        self.created_at = datetime.utcnow()
        self.processed_at: datetime | None = None

    def _generate_id(self, payload: dict) -> str:
        """Generate deterministic ID for idempotency."""
        content = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @abstractmethod
    async def process(self) -> None:
        """Process the job. Override in subclasses."""
        pass

    @abstractmethod
    async def on_failure(self, error: Exception) -> None:
        """Handle failure. Override in subclasses."""
        pass


# Example: Email job
class SendEmailJob(Job):
    async def process(self) -> None:
        await send_email(
            to=self.payload["to"],
            subject=self.payload["subject"],
            body=self.payload["body"]
        )

    async def on_failure(self, error: Exception) -> None:
        logger.error(
            "Email job failed",
            extra={
                "job_id": self.id,
                "error": str(error),
                "attempts": self.attempts
            }
        )
```

---

## Queue Integration

```python
# apps/backend/src/common/jobs/queue.py
from redis.asyncio import Redis
import json
from config import settings

class JobQueue:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.queue_name = "jobs:queue"
        self.processing_set = "jobs:processing"
        self.dead_letter = "jobs:dead_letter"

    async def enqueue(self, job: Job) -> None:
        """Add job to queue."""
        await self.redis.xadd(
            self.queue_name,
            {
                "job_id": job.id,
                "payload": json.dumps(job.payload),
                "job_type": job.__class__.__name__,
            }
        )

    async def dequeue(self, timeout: int = 5) -> list[dict] | None:
        """Get next job from queue."""
        result = await self.redis.xread(
            {self.queue_name: "0"},
            count=1,
            block=timeout * 1000
        )
        if not result:
            return None
        return result[0][1]

    async def complete(self, job_id: str) -> None:
        """Mark job as complete."""
        await self.redis.xdel(self.queue_name, job_id)

    async def retry(self, job_id: str, error: str) -> None:
        """Retry job with error."""
        await self.redis.xadd(
            self.queue_name,
            {
                "job_id": job_id,
                "retry": "1",
                "error": error,
            }
        )

    async def dead_letter(self, job_id: str, error: str) -> None:
        """Move to dead letter queue."""
        await self.redis.xadd(
            self.dead_letter,
            {
                "job_id": job_id,
                "error": error,
            }
        )
```

---

## Worker Process

```python
# apps/backend/src/workers/main.py
import asyncio
from common.redis import RedisPool
from common.jobs.queue import JobQueue
from common.jobs.base import Job
from modules.notifications.jobs import SendEmailJob, SendSmsJob

JOB_REGISTRY: dict[str, type[Job]] = {
    "SendEmailJob": SendEmailJob,
    "SendSmsJob": SendSmsJob,
}

async def process_job(message: dict) -> None:
    """Process a single job."""
    job_id = message["job_id"]
    job_type = message["job_type"]
    payload = json.loads(message["payload"])

    job_class = JOB_REGISTRY.get(job_type)
    if not job_class:
        logger.error(f"Unknown job type: {job_type}")
        return

    job = job_class(payload)
    job.attempts += 1

    try:
        await job.process()
        logger.info(f"Job completed: {job_id}")
    except Exception as e:
        logger.error(f"Job failed: {job_id}", exc_info=True)
        if job.attempts < job.max_attempts:
            await queue.retry(job_id, str(e))
        else:
            await job.on_failure(e)
            await queue.dead_letter(job_id, str(e))

async def main():
    """Worker main loop."""
    redis = await RedisPool.get_client()
    queue = JobQueue(redis)

    logger.info("Worker started")

    while True:
        messages = await queue.dequeue()
        if messages:
            for msg in messages:
                await process_job(msg)
        else:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| Async email | Fast response to user | Slight delay in sending |
| Async webhooks | Non-blocking | Complexity in retry logic |
| Sync payments | Immediate confirmation | User waits |
| Sync booking | Immediate confirmation | User waits |

---

## Related Documents

- [Queue Design](queue-design.md) — Queue architecture
- [Caching](caching.md) — Async cache warming
- [Error Handling](error-handling.md) — Job failure handling
