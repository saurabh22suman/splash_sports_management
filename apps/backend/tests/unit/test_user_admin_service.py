import pytest
from unittest.mock import AsyncMock, MagicMock

from auth.application.user_admin_service import UserAdminService
from auth.domain.entities import User, UserRole
from common.domain.exceptions import Validation, Conflict


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_persists():
    users = MagicMock()
    users.add = AsyncMock(side_effect=lambda u: u)
    users.get_by_email_global = AsyncMock(return_value=None)
    hasher = MagicMock()
    hasher.hash = MagicMock(return_value="$argon2id$v=19$m=19456,t=2,p=1$mockhash")

    svc = UserAdminService(users=users, hasher=hasher, tenant_id="t1")
    user = await svc.create_user(
        email="new@example.com",
        full_name="New User",
        password="supersecret-pw-1",
        roles=[UserRole.CUSTOMER],
    )

    hasher.hash.assert_called_once_with("supersecret-pw-1")
    assert user.password_hash == "$argon2id$v=19$m=19456,t=2,p=1$mockhash"
    assert user.email == "new@example.com"
    assert user.tenant_id == "t1"
    assert user.roles == [UserRole.CUSTOMER]
    users.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_rejects_tenant_admin_role():
    users = MagicMock()
    hasher = MagicMock()
    svc = UserAdminService(users=users, hasher=hasher, tenant_id="t1")

    with pytest.raises(Validation):
        await svc.create_user(
            email="x@example.com",
            full_name="X",
            password="supersecret-pw-1",
            roles=[UserRole.TENANT_ADMIN],
        )


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email():
    from common.domain.exceptions import Conflict

    users = MagicMock()
    users.get_by_email_global = AsyncMock(return_value=MagicMock())  # already exists
    hasher = MagicMock()
    svc = UserAdminService(users=users, hasher=hasher, tenant_id="t1")

    with pytest.raises(Conflict):
        await svc.create_user(
            email="dup@example.com",
            full_name="Dup",
            password="supersecret-pw-1",
            roles=[UserRole.CUSTOMER],
        )
