"""Auth interfaces package.

Exposes the HTTP router so the app factory can mount it.
"""
from __future__ import annotations

from auth.interfaces.http.router import router

__all__ = ["router"]
