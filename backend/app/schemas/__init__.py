"""Pydantic schemas for request/response validation."""
from app.schemas.common import BaseResponse, ErrorResponse, PaginatedResponse
from app.schemas.upload import UploadResponse, OCRResult, CourseData
from app.schemas.auth import AuthTokenResponse, AuthUserInfo

__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "UploadResponse",
    "OCRResult",
    "CourseData",
    "AuthTokenResponse",
    "AuthUserInfo",
]
