"""Helper utility functions."""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID
import hashlib


def generate_mrn(date_of_birth: datetime) -> str:
    """
    Generate unique MRN in format: MRN-YYYYMMDD-XXXX.
    
    Args:
        date_of_birth: Patient's date of birth
        
    Returns:
        Generated MRN string
    """
    date_str = date_of_birth.strftime('%Y%m%d')
    # Generate 4-digit sequence based on timestamp
    timestamp = datetime.now().timestamp()
    sequence = str(int(timestamp * 1000))[-4:]
    return f"MRN-{date_str}-{sequence}"


def hash_token(token: str) -> str:
    """
    Hash token for storage in revocation list.
    
    Args:
        token: JWT token string
        
    Returns:
        SHA256 hash of token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def calculate_expiry(minutes: int) -> datetime:
    """
    Calculate expiry datetime from current time.
    
    Args:
        minutes: Minutes until expiry
        
    Returns:
        Expiry datetime
    """
    return datetime.utcnow() + timedelta(minutes=minutes)


def is_expired(expiry: datetime) -> bool:
    """
    Check if datetime has expired.
    
    Args:
        expiry: Expiry datetime
        
    Returns:
        True if expired, False otherwise
    """
    return datetime.utcnow() > expiry


def paginate_query(
    query: Any,
    page: int = 1,
    page_size: int = 50
) -> tuple[Any, dict]:
    """
    Apply pagination to SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        page_size: Items per page
        
    Returns:
        Tuple of (paginated_query, metadata)
    """
    # Ensure valid page and page_size
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    paginated = query.offset(offset).limit(page_size)
    
    # Calculate metadata
    total_pages = (total_count + page_size - 1) // page_size
    
    metadata = {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }
    
    return paginated, metadata


def format_error_response(
    message: str,
    status_code: int,
    details: Optional[dict] = None
) -> dict:
    """
    Format error response consistently.
    
    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Formatted error dict
    """
    response = {
        "error": True,
        "message": message,
        "status_code": status_code
    }
    
    if details:
        response["details"] = details
    
    return response


def format_success_response(
    data: Any,
    message: Optional[str] = None,
    metadata: Optional[dict] = None
) -> dict:
    """
    Format success response consistently.
    
    Args:
        data: Response data
        message: Optional success message
        metadata: Optional metadata (pagination, etc.)
        
    Returns:
        Formatted response dict
    """
    response = {
        "success": True,
        "data": data
    }
    
    if message:
        response["message"] = message
    
    if metadata:
        response["metadata"] = metadata
    
    return response


def extract_request_metadata(request: Any) -> dict:
    """
    Extract metadata from FastAPI request for audit logging.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Metadata dict
    """
    return {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "content_type": request.headers.get("content-type")
    }
