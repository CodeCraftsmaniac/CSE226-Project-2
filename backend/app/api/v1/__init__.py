"""API v1 endpoints."""
from app.api.v1 import health, upload, auth, history, analysis

__all__ = ["health", "upload", "auth", "history", "analysis"]
