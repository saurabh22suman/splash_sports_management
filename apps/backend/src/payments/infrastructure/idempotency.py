from __future__ import annotations

import json
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol

from payments.infrastructure.models import IdempotencyKeyModel

if TYPE_CHECKING:
    from uuid import UUID

    from payments.infrastructure.repositories import IdempotencyKeyRepository


@dataclass(frozen=True)
class CachedResponse:
    tenant_id: UUID
    endpoint: str
    key: str
    request_hash: str
    response_status: int
    response_body: dict
    created_at: datetime | None
    expires_at: datetime | None


class RedisLike(Protocol):
    def get(self, k: str) -> bytes | None: ...
    def setex(self, k: str, ttl: int, v: bytes) -> None: ...


class IdempotencyStore:
    TTL_SECONDS = 60 * 60 * 24  # 24h

    def __init__(self, *, redis: RedisLike | None, repo: IdempotencyKeyRepository) -> None:
        self._redis = redis
        self._repo = repo

    def _redis_key(self, tenant_id: UUID, endpoint: str, key: str) -> str:
        return f"payments:idem:{tenant_id}:{endpoint}:{key}"

    async def get_response(
        self,
        tenant_id: UUID,
        endpoint: str,
        key: str,
        request_hash: str,
    ) -> tuple[int, dict] | None:
        # Try Redis first
        if self._redis is not None:
            try:
                raw = self._redis.get(self._redis_key(tenant_id, endpoint, key))
            except Exception:
                raw = None
            if raw is not None:
                cached = json.loads(raw)
                if cached["request_hash"] != request_hash:
                    raise ValueError("Idempotency-Key reused with different request body")
                return cached["response_status"], cached["response_body"]
        # Fall back to DB
        row = await self._repo.get(tenant_id, endpoint, key)
        if row is None:
            return None
        # Check if the row has expired
        if row.expires_at is not None and row.expires_at <= datetime.now(UTC):
            return None
        if row.request_hash != request_hash:
            raise ValueError("Idempotency-Key reused with different request body")
        return row.response_status, row.response_body

    async def store(
        self,
        tenant_id: UUID,
        endpoint: str,
        key: str,
        request_hash: str,
        response_status: int,
        response_body: dict,
    ) -> None:
        payload = json.dumps(
            {
                "request_hash": request_hash,
                "response_status": response_status,
                "response_body": response_body,
            }
        )
        if self._redis is not None:
            with suppress(Exception):
                self._redis.setex(
                    self._redis_key(tenant_id, endpoint, key),
                    self.TTL_SECONDS,
                    payload.encode(),
                )
        row = IdempotencyKeyModel(
            tenant_id=tenant_id,
            endpoint=endpoint,
            key=key,
            request_hash=request_hash,
            response_status=response_status,
            response_body=response_body,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=self.TTL_SECONDS),
        )
        await self._repo.save(row)
