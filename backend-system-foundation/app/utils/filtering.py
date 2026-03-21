"""Filtering utilities for API endpoints."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, or_
from sqlalchemy.sql import ColumnElement


class QueueFilters(BaseModel):
    """
    Filters for queue entries.
    
    Attributes:
        status: Filter by queue entry status
        min_priority: Minimum priority (1-10)
        max_priority: Maximum priority (1-10)
        from_date: Filter entries from this date
        to_date: Filter entries to this date
    """
    status: Optional[str] = Field(None, description="Filter by status")
    min_priority: Optional[int] = Field(None, ge=1, le=10, description="Minimum priority")
    max_priority: Optional[int] = Field(None, ge=1, le=10, description="Maximum priority")
    from_date: Optional[datetime] = Field(None, description="Filter from date")
    to_date: Optional[datetime] = Field(None, description="Filter to date")
    
    def apply_to_query(self, query, model):
        """
        Apply queue filters to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            model: QueueEntry model class
            
        Returns:
            Query with filters applied
        """
        conditions = self.build_conditions(model)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def build_conditions(self, model) -> List[ColumnElement]:
        """
        Build SQLAlchemy filter conditions for queue entries.
        
        Args:
            model: QueueEntry model class
            
        Returns:
            List of SQLAlchemy filter conditions
        """
        conditions = []
        
        if self.status:
            conditions.append(model.status == self.status)
        
        if self.min_priority is not None:
            conditions.append(model.priority >= self.min_priority)
        
        if self.max_priority is not None:
            conditions.append(model.priority <= self.max_priority)
        
        if self.from_date:
            conditions.append(model.arrival_time >= self.from_date)
        
        if self.to_date:
            conditions.append(model.arrival_time <= self.to_date)
        
        return conditions


class AuditLogFilters(BaseModel):
    """
    Filters for audit logs.
    
    Attributes:
        user_id: Filter by user ID
        action: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        from_date: Filter logs from this date
        to_date: Filter logs to this date
    """
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[UUID] = Field(None, description="Filter by resource ID")
    from_date: Optional[datetime] = Field(None, description="Filter from date")
    to_date: Optional[datetime] = Field(None, description="Filter to date")
    
    def apply_to_query(self, query, model):
        """
        Apply audit log filters to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            model: AuditLog model class
            
        Returns:
            Query with filters applied
        """
        conditions = self.build_conditions(model)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def build_conditions(self, model) -> List[ColumnElement]:
        """
        Build SQLAlchemy filter conditions for audit logs.
        
        Args:
            model: AuditLog model class
            
        Returns:
            List of SQLAlchemy filter conditions
        """
        conditions = []
        
        if self.user_id:
            conditions.append(model.user_id == self.user_id)
        
        if self.action:
            conditions.append(model.action == self.action)
        
        if self.resource_type:
            conditions.append(model.resource_type == self.resource_type)
        
        if self.resource_id:
            conditions.append(model.resource_id == self.resource_id)
        
        if self.from_date:
            conditions.append(model.created_at >= self.from_date)
        
        if self.to_date:
            conditions.append(model.created_at <= self.to_date)
        
        return conditions


class PatientFilters(BaseModel):
    """
    Filters for patient search.
    
    Attributes:
        mrn: Filter by Medical Record Number
        first_name: Filter by first name (case-insensitive)
        last_name: Filter by last name (case-insensitive)
        date_of_birth: Filter by date of birth
    """
    mrn: Optional[str] = Field(None, description="Medical Record Number")
    first_name: Optional[str] = Field(None, description="First name (case-insensitive)")
    last_name: Optional[str] = Field(None, description="Last name (case-insensitive)")
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")
    
    def apply_to_query(self, query, model):
        """
        Apply patient filters to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            model: Patient model class
            
        Returns:
            Query with filters applied
        """
        conditions = self.build_conditions(model)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def build_conditions(self, model) -> List[ColumnElement]:
        """
        Build SQLAlchemy filter conditions for patients.
        
        Args:
            model: Patient model class
            
        Returns:
            List of SQLAlchemy filter conditions
        """
        conditions = []
        
        if self.mrn:
            conditions.append(model.mrn == self.mrn)
        
        if self.first_name:
            # Case-insensitive search
            conditions.append(model.first_name.ilike(f"%{self.first_name}%"))
        
        if self.last_name:
            # Case-insensitive search
            conditions.append(model.last_name.ilike(f"%{self.last_name}%"))
        
        if self.date_of_birth:
            conditions.append(model.date_of_birth == self.date_of_birth)
        
        return conditions


class SortOrder(BaseModel):
    """
    Sort order specification.
    
    Attributes:
        field: Field name to sort by
        ascending: Sort in ascending order (True) or descending (False)
    """
    field: str = Field(..., description="Field name to sort by")
    ascending: bool = Field(True, description="Sort in ascending order")
    
    def apply_to_query(self, query, model):
        """
        Apply sort order to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            model: Model class with the field to sort by
            
        Returns:
            Query with sorting applied
            
        Raises:
            AttributeError: If field doesn't exist on model
        """
        if not hasattr(model, self.field):
            raise AttributeError(f"Model {model.__name__} has no field '{self.field}'")
        
        field = getattr(model, self.field)
        
        if self.ascending:
            return query.order_by(field.asc())
        else:
            return query.order_by(field.desc())


class QueueSortOptions:
    """
    Predefined sort options for queue entries.
    """
    
    @staticmethod
    def by_priority_desc():
        """Sort by priority descending (highest priority first)."""
        return SortOrder(field="priority", ascending=False)
    
    @staticmethod
    def by_priority_asc():
        """Sort by priority ascending (lowest priority first)."""
        return SortOrder(field="priority", ascending=True)
    
    @staticmethod
    def by_arrival_time_asc():
        """Sort by arrival time ascending (FIFO)."""
        return SortOrder(field="arrival_time", ascending=True)
    
    @staticmethod
    def by_arrival_time_desc():
        """Sort by arrival time descending (LIFO)."""
        return SortOrder(field="arrival_time", ascending=False)
    
    @staticmethod
    def by_created_at_asc():
        """Sort by created_at ascending."""
        return SortOrder(field="created_at", ascending=True)
    
    @staticmethod
    def by_created_at_desc():
        """Sort by created_at descending."""
        return SortOrder(field="created_at", ascending=False)
    
    @staticmethod
    def default_queue_order():
        """
        Default queue ordering: priority desc, then arrival_time asc.
        
        Returns:
            List of SortOrder objects for default queue ordering
        """
        return [
            QueueSortOptions.by_priority_desc(),
            QueueSortOptions.by_arrival_time_asc()
        ]


def apply_multiple_sorts(query, model, sort_orders: List[SortOrder]):
    """
    Apply multiple sort orders to a query.
    
    Args:
        query: SQLAlchemy query object
        model: Model class
        sort_orders: List of SortOrder objects
        
    Returns:
        Query with all sort orders applied
    """
    for sort_order in sort_orders:
        query = sort_order.apply_to_query(query, model)
    
    return query


def build_date_range_filter(
    model_field,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
) -> List[ColumnElement]:
    """
    Build date range filter conditions.
    
    Args:
        model_field: SQLAlchemy model field (e.g., model.created_at)
        from_date: Start date (inclusive)
        to_date: End date (inclusive)
        
    Returns:
        List of filter conditions
    """
    conditions = []
    
    if from_date:
        conditions.append(model_field >= from_date)
    
    if to_date:
        conditions.append(model_field <= to_date)
    
    return conditions


def build_priority_range_filter(
    model_field,
    min_priority: Optional[int] = None,
    max_priority: Optional[int] = None
) -> List[ColumnElement]:
    """
    Build priority range filter conditions.
    
    Args:
        model_field: SQLAlchemy model field (e.g., model.priority)
        min_priority: Minimum priority (1-10)
        max_priority: Maximum priority (1-10)
        
    Returns:
        List of filter conditions
    """
    conditions = []
    
    if min_priority is not None:
        conditions.append(model_field >= min_priority)
    
    if max_priority is not None:
        conditions.append(model_field <= max_priority)
    
    return conditions
