from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import auth.infrastructure.models  # noqa: F401  (register TenantModel with Base.metadata)
from auth.infrastructure.models import TenantModel
from payments.infrastructure.models import (
    InvoiceLineItemModel,
    InvoiceModel,
    PaymentModel,
    ProcessedRazorpayEventModel,
)
from payments.infrastructure.repositories import InvoiceRepository, ProcessedRazorpayEventRepository


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # Create tables manually to avoid issues with PostgreSQL-specific types
        # in auth models when using SQLite
        await conn.run_sync(TenantModel.__table__.create)
        await conn.run_sync(InvoiceModel.__table__.create)
        await conn.run_sync(InvoiceLineItemModel.__table__.create)
        await conn.run_sync(PaymentModel.__table__.create)
        await conn.run_sync(ProcessedRazorpayEventModel.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_invoice_repo_save_and_get(session):
    repo = InvoiceRepository(session)
    inv = InvoiceModel(
        id=uuid4(), tenant_id=uuid4(), customer_id=uuid4(),
        invoice_number="INV-000001", status="pending",
        subtotal_paise=150000, tax_paise=0, total_paise=150000, currency="INR",
        due_date=date(2026, 9, 1), paid_at=None, description="",
        metadata_={},
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    await repo.save(inv)
    found = await repo.get(inv.tenant_id, inv.id)
    assert found is not None
    assert found.invoice_number == "INV-000001"


async def test_invoice_repo_list_by_customer(session):
    repo = InvoiceRepository(session)
    tid = uuid4()
    cust_a, cust_b = uuid4(), uuid4()
    for cust in (cust_a, cust_b):
        inv = InvoiceModel(
            id=uuid4(), tenant_id=tid, customer_id=cust,
            invoice_number=f"INV-{cust.hex[:6]}", status="pending",
            subtotal_paise=150000, tax_paise=0, total_paise=150000, currency="INR",
            due_date=date(2026, 9, 1), paid_at=None, description="",
            metadata_={},
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        await repo.save(inv)
    only_a = await repo.list_by_customer(tid, cust_a)
    assert len(only_a) == 1
    assert only_a[0].customer_id == cust_a


async def test_processed_event_repo_dedup(session):
    repo = ProcessedRazorpayEventRepository(session)
    tid = uuid4()
    assert await repo.exists("evt_test_1") is False
    await repo.mark_processed("evt_test_1", tid, "payment.captured")
    assert await repo.exists("evt_test_1") is True
    # second call must not raise (idempotent insert: the repo silently no-ops if PK exists)
    await repo.mark_processed("evt_test_1", tid, "payment.captured")
