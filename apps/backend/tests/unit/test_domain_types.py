"""Tests for domain types - validates pure Python implementation."""
from __future__ import annotations

import pytest
from uuid import UUID

from common.domain.types import (
    CustomerId,
    EmailStr,
    FacilityId,
    ResourceId,
    BookingId,
    SlotId,
    SlugStr,
    TenantId,
    UserId,
)


class TestTenantId:
    """Test TenantId branded type."""

    def test_valid_uuid_accepted(self):
        """Valid UUID should be accepted."""
        valid_uuid = UUID("12345678-1234-5678-1234-567812345678")
        tid = TenantId(valid_uuid)
        assert isinstance(tid, UUID)
        assert tid == valid_uuid

    def test_string_uuid_accepted(self):
        """String UUID should be converted to UUID."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        tid = TenantId(uuid_str)
        assert isinstance(tid, UUID)
        assert str(tid) == uuid_str

    def test_invalid_string_rejected(self):
        """Invalid UUID string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID"):
            TenantId("not-a-uuid")

    def test_non_uuid_rejected(self):
        """Non-UUID type should raise TypeError."""
        with pytest.raises(TypeError, match="expected UUID or str"):
            TenantId(12345)


class TestUserId:
    """Test UserId branded type."""

    def test_valid_uuid_accepted(self):
        """Valid UUID should be accepted."""
        valid_uuid = UUID("87654321-4321-8765-4321-876543218765")
        uid = UserId(valid_uuid)
        assert isinstance(uid, UUID)
        assert uid == valid_uuid

    def test_string_uuid_accepted(self):
        """String UUID should be converted to UUID."""
        uuid_str = "87654321-4321-8765-4321-876543218765"
        uid = UserId(uuid_str)
        assert isinstance(uid, UUID)
        assert str(uid) == uuid_str

    def test_invalid_string_rejected(self):
        """Invalid UUID string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID"):
            UserId("invalid")


class TestCustomerId:
    """Test CustomerId branded type."""

    def test_valid_uuid_accepted(self):
        """Valid UUID should be accepted."""
        valid_uuid = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        cid = CustomerId(valid_uuid)
        assert isinstance(cid, UUID)
        assert cid == valid_uuid

    def test_string_uuid_accepted(self):
        """String UUID should be converted to UUID."""
        uuid_str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        cid = CustomerId(uuid_str)
        assert isinstance(cid, UUID)
        assert str(cid) == uuid_str


class TestFacilityId:
    """Test FacilityId branded type."""

    def test_valid_uuid_accepted(self):
        """Valid UUID should be accepted."""
        valid_uuid = UUID("facility1-0000-0000-0000-000000000001")
        fid = FacilityId(valid_uuid)
        assert isinstance(fid, UUID)
        assert fid == valid_uuid

    def test_string_uuid_accepted(self):
        """String UUID should be converted to UUID."""
        uuid_str = "facility1-0000-0000-0000-000000000001"
        fid = FacilityId(uuid_str)
        assert isinstance(fid, UUID)


class TestResourceId:
    """Test ResourceId branded type."""

    def test_valid_uuid_accepted(self):
        """Valid UUID should be accepted."""
        valid_uuid = UUID("resource1-0000-0000-0000-000000000001")
        rid = ResourceId(valid_uuid)
        assert isinstance(rid, UUID)
        assert rid == valid_uuid


class TestBookingId:
    """Test BookingId branded type."""

    def test_valid_uuid_accepted(self):
        """Valid UUID should be accepted."""
        valid_uuid = UUID("booking1-0000-0000-0000-000000000001")
        bid = BookingId(valid_uuid)
        assert isinstance(bid, UUID)
        assert bid == valid_uuid


class TestSlotId:
    """Test SlotId branded type."""

    def test_valid_uuid_accepted(self):
        """Valid UUID should be accepted."""
        valid_uuid = UUID("slot1-0000-0000-0000-000000000001")
        sid = SlotId(valid_uuid)
        assert isinstance(sid, UUID)
        assert sid == valid_uuid


class TestEmailStr:
    """Test EmailStr validated string type."""

    def test_valid_email_accepted(self):
        """Valid email should be accepted."""
        email = EmailStr("user@example.com")
        assert isinstance(email, str)
        assert email == "user@example.com"

    def test_email_with_plus_addressing(self):
        """Email with + addressing should be accepted."""
        email = EmailStr("user+tag@example.com")
        assert isinstance(email, str)
        assert email == "user+tag@example.com"

    def test_email_with_subdomain(self):
        """Email with subdomain should be accepted."""
        email = EmailStr("user@sub.domain.example.com")
        assert isinstance(email, str)

    def test_invalid_email_rejected(self):
        """Invalid email should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid email"):
            EmailStr("not-an-email")

    def test_email_without_at_rejected(self):
        """Email without @ should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid email"):
            EmailStr("userexample.com")

    def test_email_without_domain_rejected(self):
        """Email without domain should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid email"):
            EmailStr("user@")

    def test_empty_email_rejected(self):
        """Empty email should raise ValueError."""
        with pytest.raises(ValueError):
            EmailStr("")


class TestSlugStr:
    """Test SlugStr validated string type."""

    def test_valid_slug_accepted(self):
        """Valid slug should be accepted."""
        slug = SlugStr("valid-slug")
        assert isinstance(slug, str)
        assert slug == "valid-slug"

    def test_slug_single_segment(self):
        """Single segment slug should be accepted."""
        slug = SlugStr("abc")
        assert isinstance(slug, str)
        assert slug == "abc"

    def test_slug_with_numbers(self):
        """Slug with numbers should be accepted."""
        slug = SlugStr("slug123")
        assert isinstance(slug, str)
        assert slug == "slug123"

    def test_invalid_slug_with_uppercase_rejected(self):
        """Slug with uppercase should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid slug"):
            SlugStr("Invalid-Slug")

    def test_invalid_slug_starts_with_hyphen(self):
        """Slug starting with hyphen should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid slug"):
            SlugStr("-starts-with-hyphen")

    def test_invalid_slug_ends_with_hyphen(self):
        """Slug ending with hyphen should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid slug"):
            SlugStr("ends-with-hyphen-")

    def test_invalid_slug_too_long_rejected(self):
        """Slug exceeding max length should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid slug"):
            SlugStr("a" * 41)

    def test_empty_slug_rejected(self):
        """Empty slug should raise ValueError."""
        with pytest.raises(ValueError):
            SlugStr("")


class TestPhoneStr:
    """Test PhoneStr validated string type."""

    def test_valid_phone_accepted(self):
        """Valid phone number should be accepted."""
        phone = PhoneStr("+1234567890")
        assert isinstance(phone, str)
        assert phone == "+1234567890"

    def test_phone_with_spaces(self):
        """Phone with spaces should be accepted."""
        phone = PhoneStr("+1 234 567 890")
        assert isinstance(phone, str)

    def test_phone_with_dashes(self):
        """Phone with dashes should be accepted."""
        phone = PhoneStr("+1-234-567-890")
        assert isinstance(phone, str)

    def test_phone_with_parentheses(self):
        """Phone with parentheses should be accepted."""
        phone = PhoneStr("+1 (234) 567-890")
        assert isinstance(phone, str)

    def test_invalid_phone_rejected(self):
        """Invalid phone should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid phone"):
            PhoneStr("abc")

    def test_phone_too_short_rejected(self):
        """Phone too short should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid phone"):
            PhoneStr("+1")

    def test_phone_too_long_rejected(self):
        """Phone too long should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid phone"):
            PhoneStr("+" + "1" * 25)
