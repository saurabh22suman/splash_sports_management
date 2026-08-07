from payments.domain.value_objects import Money, InvoiceStatus, PaymentStatus, RefundStatus
import pytest

class TestMoney:
    def test_construction(self):
        m = Money(amount_paise=150000, currency="INR")  # ₹1500.00
        assert m.amount_paise == 150000
        assert m.currency == "INR"

    def test_invalid_negative(self):
        with pytest.raises(ValueError):
            Money(amount_paise=-1, currency="INR")

    def test_invalid_currency_length(self):
        with pytest.raises(ValueError):
            Money(amount_paise=100, currency="IN")  # too short

    def test_equality(self):
        a = Money(150000, "INR")
        b = Money(150000, "INR")
        c = Money(150000, "USD")
        assert a == b
        assert a != c

class TestEnums:
    def test_invoice_status_members(self):
        assert {s.value for s in InvoiceStatus} == {"draft", "pending", "paid", "failed", "cancelled", "refunded"}

    def test_payment_status_members(self):
        # Razorpay flow: pending → captured or failed (no separate "authorized" — Razorpay auto-captures)
        assert {s.value for s in PaymentStatus} == {"pending", "captured", "failed"}

    def test_refund_status_members(self):
        assert {s.value for s in RefundStatus} == {"pending", "completed", "failed"}
