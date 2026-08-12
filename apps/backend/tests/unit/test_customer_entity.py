"""Unit tests for Customer entity."""

from __future__ import annotations

from datetime import date, timezone
from uuid import uuid4

import pytest

from common.domain.exceptions import Validation
from customer.domain.entities import Customer, CustomerStatus


@pytest.mark.unit
class TestCustomerEntity:
    def test_create_with_valid_data(self) -> None:
        c = Customer.create(
            tenant_id=uuid4(),
            user_id=uuid4(),
            full_name="Alice",
            email="alice@example.com",
        )
        assert c.full_name == "Alice"
        assert c.email == "alice@example.com"
        assert c.status == CustomerStatus.ACTIVE

    def test_email_is_lowercased_and_stripped(self) -> None:
        c = Customer.create(
            tenant_id=uuid4(),
            user_id=uuid4(),
            full_name="Alice",
            email="  Alice@Example.COM  ",
        )
        assert c.email == "alice@example.com"

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(Validation):
            Customer.create(
                tenant_id=uuid4(),
                user_id=uuid4(),
                full_name="   ",
                email="alice@example.com",
            )

    def test_rejects_invalid_email(self) -> None:
        with pytest.raises(Validation):
            Customer.create(
                tenant_id=uuid4(),
                user_id=uuid4(),
                full_name="Alice",
                email="not-an-email",
            )

    def test_rejects_invalid_phone(self) -> None:
        with pytest.raises(Validation):
            Customer.create(
                tenant_id=uuid4(),
                user_id=uuid4(),
                full_name="Alice",
                email="alice@example.com",
                phone="not-a-phone",
            )

    def test_ban_blocks_reactivation(self) -> None:
        c = Customer.create(
            tenant_id=uuid4(),
            user_id=uuid4(),
            full_name="Alice",
            email="alice@example.com",
        )
        c.ban()
        assert c.status == CustomerStatus.BANNED
        c.activate()
        # Cannot activate a banned customer
        assert c.status == CustomerStatus.BANNED
