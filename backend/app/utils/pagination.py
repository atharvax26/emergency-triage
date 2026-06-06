"""Pagination utilities for API endpoints."""

from typing import Generic, List, TypeVar
from math import ceil

from pydantic import BaseModel, Field


T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Pagination parameters for API requests.
    
    Attributes:
        page: Page number (starts at 1)
        page_size: Number of items per page
    """
    page: int = Field(default=1, ge=1, description="Page number (starts at 1)")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page (max 100)")
    
    def get_offset(self) -> int:
        """
        Calculate the database offset for the current page.
        
        Returns:
            Offset value for database query
        """
        return (self.page - 1) * self.page_size
    
    def get_limit(self) -> int:
        """
        Get the limit for database query.
        
        Returns:
            Limit value (same as page_size)
        """
        return self.page_size


class PaginationMetadata(BaseModel):
    """
    Pagination metadata for API responses.
    
    Attributes:
        total_count: Total number of items matching criteria
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
    """
    total_count: int = Field(..., description="Total number of items matching criteria")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    @classmethod
    def create(cls, total_count: int, page: int, page_size: int) -> "PaginationMetadata":
        """
        Create pagination metadata from total count and pagination params.
        
        Args:
            total_count: Total number of items
            page: Current page number
            page_size: Items per page
            
        Returns:
            PaginationMetadata instance
        """
        total_pages = ceil(total_count / page_size) if total_count > 0 else 1
        
        return cls(
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response model.
    
    Type Parameters:
        T: Type of items in the response
        
    Attributes:
        items: List of items for current page
        total_count: Total number of items matching criteria
        page: Current page number
        page_size: Items per page
        total_pages: Total number of pages
    """
    items: List[T] = Field(..., description="List of items for current page")
    total_count: int = Field(..., description="Total number of items matching criteria")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total_count: int,
        pagination: PaginationParams
    ) -> "PaginatedResponse[T]":
        """
        Create a paginated response from items and pagination params.
        
        Args:
            items: List of items for current page
            total_count: Total number of items matching criteria
            pagination: Pagination parameters
            
        Returns:
            PaginatedResponse instance
        """
        metadata = PaginationMetadata.create(
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        return cls(
            items=items,
            total_count=metadata.total_count,
            page=metadata.page,
            page_size=metadata.page_size,
            total_pages=metadata.total_pages
        )


def paginate_query(query, pagination: PaginationParams):
    """
    Apply pagination to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        pagination: Pagination parameters
        
    Returns:
        Query with limit and offset applied
    """
    return query.offset(pagination.get_offset()).limit(pagination.get_limit())
