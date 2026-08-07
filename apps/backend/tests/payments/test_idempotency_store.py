from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from payments.infrastructure.idempotency import CachedResponse, IdempotencyStore


@pytest.fixture
def fake_redis():
    r = MagicMock()
    store = {}

    def get(k):
        return store.get(k)

    def setex(k, ttl, v):
        store[k] = v

    r.get = MagicMock(side_effect=get)
    r.setex = MagicMock(side_effect=setex)
    # Store reference for synchronous access in tests
    r._store = store
    return r


@pytest.fixture
def fake_repo():
    r = MagicMock()
    r.get = AsyncMock()
    r.save = AsyncMock()
    return r


async def test_store_returns_none_when_missing(fake_redis, fake_repo):
    fake_repo.get.return_value = None
    s = IdempotencyStore(redis=fake_redis, repo=fake_repo)
    result = await s.get_response(uuid4(), "POST /foo", "k1", "hash-abc")
    assert result is None


async def test_store_returns_cached_response(fake_redis, fake_repo):
    tid = uuid4()
    fake_repo.get.return_value = CachedResponse(
        tenant_id=tid, endpoint="POST /foo", key="k1",
        request_hash="hash-abc", response_status=201,
        response_body={"id": "abc"}, created_at=None, expires_at=None,
    )
    s = IdempotencyStore(redis=fake_redis, repo=fake_repo)
    status, body = await s.get_response(tid, "POST /foo", "k1", "hash-abc")
    assert status == 201
    assert body == {"id": "abc"}


async def test_store_writes_to_redis_then_db(fake_redis, fake_repo):
    s = IdempotencyStore(redis=fake_redis, repo=fake_repo)
    await s.store(
        uuid4(), "POST /foo", "k1", "hash-abc",
        201, {"id": "x"}
    )
    assert fake_redis.setex.called
    assert fake_repo.save.called


async def test_store_falls_back_to_db_when_redis_down(fake_repo):
    fake_redis = MagicMock()
    fake_redis.get = MagicMock(side_effect=ConnectionError("redis down"))
    s = IdempotencyStore(redis=fake_redis, repo=fake_repo)
    fake_repo.get.return_value = None
    result = await s.get_response(uuid4(), "POST /foo", "k1", "hash-abc")
    assert result is None
    assert fake_repo.get.called


async def test_db_expiry_returns_none_when_expired(fake_redis, fake_repo):
    """When Redis misses and DB row's expires_at is at or before now, treat as absent."""
    tid = uuid4()
    # Row exists but is expired
    expired_time = datetime.now(UTC) - timedelta(hours=1)
    fake_repo.get.return_value = CachedResponse(
        tenant_id=tid, endpoint="POST /foo", key="k1",
        request_hash="hash-abc", response_status=201,
        response_body={"id": "abc"}, created_at=expired_time, expires_at=expired_time,
    )
    # Redis returns nothing
    fake_redis.get.return_value = None
    s = IdempotencyStore(redis=fake_redis, repo=fake_repo)
    result = await s.get_response(tid, "POST /foo", "k1", "hash-abc")
    assert result is None


async def test_db_expiry_returns_response_when_not_expired(fake_redis, fake_repo):
    """When Redis misses but DB row is still valid, return the cached response."""
    tid = uuid4()
    future_time = datetime.now(UTC) + timedelta(hours=1)
    fake_repo.get.return_value = CachedResponse(
        tenant_id=tid, endpoint="POST /foo", key="k1",
        request_hash="hash-abc", response_status=201,
        response_body={"id": "abc"}, created_at=datetime.now(UTC), expires_at=future_time,
    )
    # Redis returns nothing - fallback to DB
    fake_redis.get.return_value = None
    s = IdempotencyStore(redis=fake_redis, repo=fake_repo)
    result = await s.get_response(tid, "POST /foo", "k1", "hash-abc")
    assert result == (201, {"id": "abc"})
