# Background Tasks

> This document covers background job processing with Arq, job design patterns, retry policies, and scheduling.

## Overview

We use **Arq** (asyncio Redis queue) for background task processing. Background tasks handle:

- Sending emails/SMS
- Processing webhooks
- Generating reports
- Cleanup jobs
- Event relay to consumers

## Why Arq

| Feature | Arq | Celery |
|---------|-----|--------|
| Async support | Native | Requires threads |
| Broker | Redis only | Redis, RabbitMQ, SQS |
| Dependencies | Lightweight | Heavy |
| Learning curve | Low | Medium |

## Job Design

### Basic Job

```python
# src/notifications/jobs.py
from arq import create_pool
from arq.connections import RedisSettings
from pydantic import BaseModel


class SendEmailJob(BaseModel):
    """Job to send an email."""
    to: str
    subject: str
    body: str
    from_email: str = "noreply@splashh.com"


async def send_email(ctx: dict, job: SendEmailJob) -> dict:
    """Send email job."""
    logger = ctx["logger"]

    logger.info("Sending email", to=job.to, subject=job.subject)

    # Actual email sending logic
    await email_service.send(
        to=job.to,
        subject=job.subject,
        body=job.body,
        from_email=job.from_email,
    )

    return {"status": "sent", "to": job.to}
```

### Job with Dependencies

```python
# src/booking/jobs.py
from datetime import datetime


class ProcessBookingCompletionJob:
    """Job to process a completed booking."""
    booking_id: str


async def process_booking_completion(ctx: dict, job: ProcessBookingCompletionJob) -> dict:
    """Process completed booking - update stats, send notifications."""
    logger = ctx["logger"]
    booking_id = job.booking_id

    logger.info("Processing booking completion", booking_id=booking_id)

    # 1. Update analytics
    await analytics_service.record_booking_completed(booking_id)

    # 2. Send confirmation
    await notification_service.send_booking_completed(booking_id)

    # 3. Check for follow-up
    await check_and_create_follow_up_booking(booking_id)

    return {"status": "processed", "booking_id": booking_id}
```

## Worker Configuration

```python
# src/worker.py
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker

from notifications.jobs import send_email
from booking.jobs import process_booking_completion
from common.config import get_settings


async def main():
    settings = get_settings()

    # Create worker class
    class MyWorker(Worker):
        redis_settings = RedisSettings.from_url(settings.redis_url)
        functions = [
            send_email,
            process_booking_completion,
        ]
        # Job timeout
        job_timeout = 300  # 5 minutes
        # Keep results for 24 hours
        keep_result_days = 1
        # Retry settings
        max_retries = 3
        retry_delay = 60  # seconds

    # Run worker
    worker = MyWorker()
    await worker.main()
```

## Retry Policies

```python
# src/common/retry.py
from datetime import timedelta


# Exponential backoff: 1s, 5s, 30s, 5m, 30m, 2h
def calculate_retry_delay(attempt: int) -> timedelta:
    """Calculate retry delay with exponential backoff."""
    delays = [
        timedelta(seconds=1),
        timedelta(seconds=5),
        timedelta(seconds=30),
        timedelta(minutes=5),
        timedelta(minutes=30),
        timedelta(hours=2),
    ]
    return delays[min(attempt, len(delays) - 1)]


# Configure in worker
class MyWorker(Worker):
    functions = [send_email]

    async def retry_message(
        self,
        ctx: dict,
        job: "ArqJob",
        result: Exception,
        retry_count: int,
    ) -> None:
        """Custom retry logic."""
        delay = calculate_retry_delay(retry_count)
        await job.delay(delay)
```

## Job Enqueuement

```python
# src/booking/application/services.py
from arq import enqueue_job


class BookingService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    def create_booking(self, command: CreateBookingCommand) -> BookingResult:
        # ... create booking ...

        # Enqueue background job
        await enqueue_job(
            "process_booking_completion",
            ProcessBookingCompletionJob(booking_id=str(booking.id)),
            delay=0,  # Execute immediately
        )

        return BookingResult.from_entity(booking)
```

## Cron Jobs

Arq doesn't have built-in cron, so we use **croniter** or external cron:

```python
# src/worker_cron.py
import croniter
from datetime import datetime, timedelta


async def cleanup_old_bookings(ctx: dict) -> dict:
    """Clean up bookings older than 30 days."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    count = await booking_repo.delete_older_than(cutoff)
    return {"deleted": count}


class CronWorker(Worker):
    async def main(self):
        while True:
            # Run cron jobs
            await self.run_crons()

            # Sleep until next minute
            await asyncio.sleep(60)

    async def run_crons(self):
        now = datetime.utcnow()
        cron = croniter.croniter("0 3 * * *", now)  # Daily at 3 AM

        if cron.is_now():
            await self.enqueue_job("cleanup_old_bookings")
```

## Idempotent Jobs

> **Rule** — Every background job must be idempotent.

```python
# src/notifications/jobs.py
async def send_email(ctx: dict, job: SendEmailJob) -> dict:
    """Idempotent email sending."""
    logger = ctx["logger"]

    # Generate idempotency key from job parameters
    idempotency_key = f"email:{job.to}:{job.subject}:{hash(job.body)}"

    # Check if already processed
    if await redis.exists(idempotency_key):
        logger.info("Email already sent", key=idempotency_key)
        return {"status": "already_sent", "key": idempotency_key}

    # Send email
    await email_service.send(...)

    # Mark as processed (24h TTL)
    await redis.setex(idempotency_key, 86400, "sent")

    return {"status": "sent"}
```

## Monitoring

```python
# src/common/monitoring.py
from prometheus_client import Counter, Histogram

jobs_total = Counter(
    "background_jobs_total",
    "Total background jobs",
    ["job_name", "status"]
)

job_duration = Histogram(
    "background_job_duration_seconds",
    "Background job duration",
    ["job_name"]
)


# Wrap job execution
async def monitored_job(func):
    async def wrapper(ctx: dict, *args, **kwargs):
        start = time.time()
        try:
            result = await func(ctx, *args, **kwargs)
            jobs_total.labels(job_name=func.__name__, status="success").inc()
            return result
        except Exception as e:
            jobs_total.labels(job_name=func.__name__, status="error").inc()
            raise
        finally:
            job_duration.labels(job_name=func.__name__).observe(time.time() - start)

    return wrapper
```

## Testing Jobs

```python
# tests/background/test_jobs.py
import pytest
from unittest.mock import AsyncMock, patch

from notifications.jobs import send_email, SendEmailJob


@pytest.fixture
def mock_email_service():
    return AsyncMock()


@pytest.mark.asyncio
async def test_send_email_success(mock_email_service):
    job = SendEmailJob(
        to="user@example.com",
        subject="Test",
        body="Test body",
    )

    with patch("notifications.jobs.email_service", mock_email_service):
        result = await send_email({}, job)

    assert result["status"] == "sent"
    mock_email_service.send.assert_called_once()
```

## Deployment

```yaml
# docker-compose.yml
worker:
  build: .
  command: python -m worker
  environment:
    - REDIS_URL=redis://redis:6379/0
    - DATABASE_URL=postgresql://...
  depends_on:
    - redis
    - postgres
  restart: unless-stopped
  deploy:
    replicas: 2  # Run multiple workers
```

## Related Documents

- [Event Bus](../07-events/event-bus.md)
- [Retry & Failure](../07-events/retry-failure.md)
- [Arq Documentation](https://arq-docs.helpmanual.io/)
