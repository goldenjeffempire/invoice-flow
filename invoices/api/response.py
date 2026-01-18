from typing import Any, Optional, Dict
from rest_framework.response import Response

class APIResponse:
    """Standardized API response format."""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        meta: Optional[dict] = None,
        success: bool = True
    ) -> Response:
        """Return a successful API response."""
        response_data = {
            "success": success,
            "message": message,
        }
        if data is not None:
            response_data["data"] = data
        if meta:
            response_data["meta"] = meta
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(
        code: str,
        message: str = "An error occurred",
        details: Optional[Any] = None,
        status_code: int = 400,
    ) -> Response:
        """Return an error API response."""
        response_data = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        }
        if details:
            response_data["error"]["details"] = details
        return Response(response_data, status=status_code)
    
    @staticmethod
    def paginated(
        data: Any,
        page: int,
        page_size: int,
        total: int,
        message: str = "Success",
        status_code: int = 200,
    ) -> Response:
        """Return paginated response with metadata."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        response_data = {
            "success": True,
            "message": message,
            "data": data,
            "meta": {
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                }
            }
        }
        return Response(response_data, status=status_code)