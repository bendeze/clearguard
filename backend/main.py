"""ClearGuard FastAPI Entry Point Bridge.

Forwards to the modular application package at app.main:app.
"""

from app.main import app

__all__ = ["app"]
