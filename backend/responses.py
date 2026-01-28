"""
Standardized API response models and utilities.

FEATURES:
- Consistent response structure across all endpoints
- Proper error handling and status codes
- Pagination support
- Metadata inclusion
"""

from typing import Optional, Any, Generic, TypeVar, List
from datetime import datetime

from pydantic import BaseModel
from fastapi import status

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper.
    
    Usage:
        return APIResponse(
            success=True,
            data={"forecast": forecast_data},
            message="Forecast generated successfully"
        )
    """
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    metadata: Optional[dict] = None
    timestamp: str = datetime.utcnow().isoformat()


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response.
    
    Usage:
        return PaginatedResponse(
            success=True,
            data=items,
            total=100,
            page=1,
            page_size=20,
            total_pages=5
        )
    """
    success: bool
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    message: Optional[str] = None
    timestamp: str = datetime.utcnow().isoformat()


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: str = datetime.utcnow().isoformat()


# -------------------------------------------------
# Response Builders
# -------------------------------------------------
def success_response(
    data: Any,
    message: Optional[str] = None,
    metadata: Optional[dict] = None
) -> APIResponse:
    """Build a success response."""
    return APIResponse(
        success=True,
        data=data,
        message=message,
        metadata=metadata
    )


def error_response(
    error: str,
    detail: Optional[str] = None,
    error_code: Optional[str] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
) -> ErrorResponse:
    """Build an error response."""
    return ErrorResponse(
        error=error,
        detail=detail,
        error_code=error_code
    )


def paginated_response(
    data: List[Any],
    total: int,
    page: int,
    page_size: int,
    message: Optional[str] = None
) -> PaginatedResponse:
    """Build a paginated response."""
    total_pages = (total + page_size - 1) // page_size  # Ceiling division
    
    return PaginatedResponse(
        success=True,
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message=message
    )
