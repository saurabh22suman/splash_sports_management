"""GREEN — minimal implementation to make the test pass.

We use Argon2id with OWASP-recommended parameters.
"""
from __future__ import annotations

from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import VerifyMismatchError


class Argon2PasswordHasher:
    """Argon2id password hasher.

    Parameters follow OWASP 2024 recommendations:
    - memory_cost: 19456 KiB (~19 MB)
    - time_cost: 2 iterations
    - parallelism: 1
    """

    def __init__(
        self,
        *,
        time_cost: int = 2,
        memory_cost: int = 19456,
        parallelism: int = 1,
    ) -> None:
        self._hasher = _Argon2(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, hashed: str, password: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except VerifyMismatchError:
            return False
        except Exception:  # malformed hash, etc.
            return False
