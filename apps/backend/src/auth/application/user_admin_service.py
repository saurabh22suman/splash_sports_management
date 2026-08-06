from __future__ import annotations

from uuid import UUID

from auth.domain.entities import User, UserRole
from auth.infrastructure.password_hasher import Argon2PasswordHasher
from auth.infrastructure.repositories import UserRepository
from common.domain.exceptions import Conflict, Validation

ALLOWED_NEW_USER_ROLES = {UserRole.CUSTOMER, UserRole.STAFF}


class UserAdminService:
    def __init__(
        self,
        users: UserRepository,
        hasher: Argon2PasswordHasher,
        tenant_id: UUID,
    ) -> None:
        self.users = users
        self.hasher = hasher
        self.tenant_id = tenant_id

    async def create_user(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
        roles: list[UserRole],
    ) -> User:
        if any(r not in ALLOWED_NEW_USER_ROLES for r in roles):
            raise Validation("Only customer and staff roles can be assigned via this endpoint")
        if not roles:
            raise Validation("At least one role is required")

        existing = await self.users.get_by_email_global(email)
        if existing is not None:
            raise Conflict("User with that email already exists", details={"email": email})

        user = User.create(
            tenant_id=self.tenant_id,
            email=email,
            password_hash=self.hasher.hash(password),
            full_name=full_name,
            roles=roles,
        )
        return await self.users.add(user)

    async def list_users(self) -> list[User]:
        return await self.users.list_by_tenant(self.tenant_id)
