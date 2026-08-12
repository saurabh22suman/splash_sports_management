"""RED — failing test first.

This test defines the contract for [`PasswordHasher`]:
- hash() returns a non-empty string different from the input
- verify() accepts the correct password and rejects others
"""

from __future__ import annotations

import pytest

from auth.infrastructure.password_hasher import Argon2PasswordHasher


@pytest.mark.unit
class TestPasswordHasher:
    def test_hash_returns_non_empty_string(self) -> None:
        hasher = Argon2PasswordHasher()
        h = hasher.hash("correct horse battery staple")
        assert isinstance(h, str)
        assert len(h) > 20
        assert h != "correct horse battery staple"

    def test_hash_produces_different_output_each_time(self) -> None:
        hasher = Argon2PasswordHasher()
        h1 = hasher.hash("hunter2")
        h2 = hasher.hash("hunter2")
        # Argon2 uses random salt; hashes differ
        assert h1 != h2

    def test_verify_accepts_correct_password(self) -> None:
        hasher = Argon2PasswordHasher()
        h = hasher.hash("correct horse battery staple")
        assert hasher.verify(h, "correct horse battery staple") is True

    def test_verify_rejects_wrong_password(self) -> None:
        hasher = Argon2PasswordHasher()
        h = hasher.hash("correct horse battery staple")
        assert hasher.verify(h, "wrong password") is False

    def test_verify_rejects_empty_password(self) -> None:
        hasher = Argon2PasswordHasher()
        h = hasher.hash("something")
        assert hasher.verify(h, "") is False
