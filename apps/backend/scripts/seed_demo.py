"""Seed a demo 'Splash Sports Club' facility for the first/only dev tenant.

Idempotent: re-runs are no-ops once a facility with slug 'splash-sports-club'
exists for the target tenant.

Run via:
    make -C apps/backend seed-demo
or directly:
    PYTHONPATH=src uv run python apps/backend/scripts/seed_demo.py
"""
from __future__ import annotations

import sys
from typing import TextIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

# Exit codes
EXIT_OK = 0
EXIT_NO_TENANT = 1


async def seed_demo(session: AsyncSession, *, stdout: TextIO = sys.stdout) -> int:
    """Seed the demo facility. Returns the process exit code."""
    return EXIT_OK


if __name__ == "__main__":
    # CLI wrapper is added in Task 5.
    raise SystemExit("CLI not yet wired — see Task 5")
