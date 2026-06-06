"""Unit tests for pagination and filtering utilities."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.utils.pagination import (
    PaginationParams,
    PaginationMetadata,
    PaginatedResponse,
    paginate_query,
)
from app.utils.filtering import (
    QueueFilters,
    AuditLogFilters,
    PatientFilters,
    SortOrder,
    QueueSortOptions,
    apply_multiple_sorts,
    build_date_range_filter,
    build_priority_range_filter,
)


class TestPaginationParams:
    """Test PaginationParams class."""
    
    def test_default_values(self):
        """Test default pagination values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 50
    
    def test_custom_values(self):
        """Test custom pagination values."""
        params = PaginationParams(page=3, page_size=25)
        assert params.page == 3
        assert params.page_size == 25
    
    def test_get_offset(self):
        """Test offset calculation."""
        params = PaginationParams(page=1, page_size=50)
        assert params.get_offset() == 0
        
        params = PaginationParams(page=2, page_size=50)
        assert params.get_offset() == 50
        
        params = PaginationParams(page=3, page_size=25)
        assert params.get_offset() == 50
    
    def test_get_limit(self):
        """Test limit calculation."""
        params = PaginationParams(page=1, page_size=50)
        assert params.get_limit() == 50
        
        params = PaginationParams(page=2, page_size=25)
        assert params.get_limit() == 25
    
    def test_page_size_max_constraint(self):
        """Test page_size max constraint."""
        with pytest.raises(ValueError):
            PaginationParams(page=1, page_size=101)
    
    def test_page_min_constraint(self):
        """Test page min constraint."""
        with pytest.raises(ValueError):
            PaginationParams(page=0, page_size=50)


class TestPaginationMetadata:
    """Test PaginationMetadata class."""
    
    def test_create_metadata(self):
        """Test creating pagination metadata."""
        metadata = PaginationMetadata.create(
            total_count=100,
            page=1,
            page_size=50
        )
        
        assert metadata.total_count == 100
        assert metadata.page == 1
        assert metadata.page_size == 50
        assert metadata.total_pages == 2
    
    def test_create_metadata_with_remainder(self):
        """Test creating metadata with remainder."""
        metadata = PaginationMetadata.create(
            total_count=105,
            page=1,
            page_size=50
        )
        
        assert metadata.total_count == 105
        assert metadata.total_pages == 3
    
    def test_create_metadata_empty(self):
        """Test creating metadata with no items."""
        metadata = PaginationMetadata.create(
            total_count=0,
            page=1,
            page_size=50
        )
        
        assert metadata.total_count == 0
        assert metadata.total_pages == 1
    
    def test_create_metadata_single_page(self):
        """Test creating metadata with single page."""
        metadata = PaginationMetadata.create(
            total_count=25,
            page=1,
            page_size=50
        )
        
        assert metadata.total_count == 25
        assert metadata.total_pages == 1


class TestPaginatedResponse:
    """Test PaginatedResponse class."""
    
    def test_create_paginated_response(self):
        """Test creating paginated response."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        pagination = PaginationParams(page=1, page_size=50)
        
        response = PaginatedResponse.create(
            items=items,
            total_count=100,
            pagination=pagination
        )
        
        assert len(response.items) == 3
        assert response.total_count == 100
        assert response.page == 1
        assert response.page_size == 50
        assert response.total_pages == 2


class TestQueueFilters:
    """Test QueueFilters class."""
    
    def test_empty_filters(self):
        """Test empty filters."""
        filters = QueueFilters()
        assert filters.status is None
        assert filters.min_priority is None
        assert filters.max_priority is None
        assert filters.from_date is None
        assert filters.to_date is None
    
    def test_status_filter(self):
        """Test status filter."""
        filters = QueueFilters(status="waiting")
        assert filters.status == "waiting"
    
    def test_priority_range_filter(self):
        """Test priority range filter."""
        filters = QueueFilters(min_priority=3, max_priority=8)
        assert filters.min_priority == 3
        assert filters.max_priority == 8
    
    def test_date_range_filter(self):
        """Test date range filter."""
        from_date = datetime(2024, 1, 1)
        to_date = datetime(2024, 12, 31)
        
        filters = QueueFilters(from_date=from_date, to_date=to_date)
        assert filters.from_date == from_date
        assert filters.to_date == to_date
    
    def test_priority_constraints(self):
        """Test priority constraints."""
        with pytest.raises(ValueError):
            QueueFilters(min_priority=0)
        
        with pytest.raises(ValueError):
            QueueFilters(max_priority=11)


class TestAuditLogFilters:
    """Test AuditLogFilters class."""
    
    def test_empty_filters(self):
        """Test empty filters."""
        filters = AuditLogFilters()
        assert filters.user_id is None
        assert filters.action is None
        assert filters.resource_type is None
        assert filters.resource_id is None
        assert filters.from_date is None
        assert filters.to_date is None
    
    def test_user_id_filter(self):
        """Test user_id filter."""
        user_id = uuid4()
        filters = AuditLogFilters(user_id=user_id)
        assert filters.user_id == user_id
    
    def test_action_filter(self):
        """Test action filter."""
        filters = AuditLogFilters(action="patient.create")
        assert filters.action == "patient.create"
    
    def test_resource_type_filter(self):
        """Test resource_type filter."""
        filters = AuditLogFilters(resource_type="patient")
        assert filters.resource_type == "patient"
    
    def test_resource_id_filter(self):
        """Test resource_id filter."""
        resource_id = uuid4()
        filters = AuditLogFilters(resource_id=resource_id)
        assert filters.resource_id == resource_id
    
    def test_date_range_filter(self):
        """Test date range filter."""
        from_date = datetime(2024, 1, 1)
        to_date = datetime(2024, 12, 31)
        
        filters = AuditLogFilters(from_date=from_date, to_date=to_date)
        assert filters.from_date == from_date
        assert filters.to_date == to_date


class TestPatientFilters:
    """Test PatientFilters class."""
    
    def test_empty_filters(self):
        """Test empty filters."""
        filters = PatientFilters()
        assert filters.mrn is None
        assert filters.first_name is None
        assert filters.last_name is None
        assert filters.date_of_birth is None
    
    def test_mrn_filter(self):
        """Test MRN filter."""
        filters = PatientFilters(mrn="MRN-20240101-0001")
        assert filters.mrn == "MRN-20240101-0001"
    
    def test_name_filters(self):
        """Test name filters."""
        filters = PatientFilters(first_name="John", last_name="Doe")
        assert filters.first_name == "John"
        assert filters.last_name == "Doe"
    
    def test_date_of_birth_filter(self):
        """Test date of birth filter."""
        dob = datetime(1990, 1, 1)
        filters = PatientFilters(date_of_birth=dob)
        assert filters.date_of_birth == dob


class TestSortOrder:
    """Test SortOrder class."""
    
    def test_ascending_sort(self):
        """Test ascending sort order."""
        sort = SortOrder(field="priority", ascending=True)
        assert sort.field == "priority"
        assert sort.ascending is True
    
    def test_descending_sort(self):
        """Test descending sort order."""
        sort = SortOrder(field="priority", ascending=False)
        assert sort.field == "priority"
        assert sort.ascending is False


class TestQueueSortOptions:
    """Test QueueSortOptions class."""
    
    def test_by_priority_desc(self):
        """Test sort by priority descending."""
        sort = QueueSortOptions.by_priority_desc()
        assert sort.field == "priority"
        assert sort.ascending is False
    
    def test_by_priority_asc(self):
        """Test sort by priority ascending."""
        sort = QueueSortOptions.by_priority_asc()
        assert sort.field == "priority"
        assert sort.ascending is True
    
    def test_by_arrival_time_asc(self):
        """Test sort by arrival time ascending."""
        sort = QueueSortOptions.by_arrival_time_asc()
        assert sort.field == "arrival_time"
        assert sort.ascending is True
    
    def test_by_arrival_time_desc(self):
        """Test sort by arrival time descending."""
        sort = QueueSortOptions.by_arrival_time_desc()
        assert sort.field == "arrival_time"
        assert sort.ascending is False
    
    def test_by_created_at_asc(self):
        """Test sort by created_at ascending."""
        sort = QueueSortOptions.by_created_at_asc()
        assert sort.field == "created_at"
        assert sort.ascending is True
    
    def test_by_created_at_desc(self):
        """Test sort by created_at descending."""
        sort = QueueSortOptions.by_created_at_desc()
        assert sort.field == "created_at"
        assert sort.ascending is False
    
    def test_default_queue_order(self):
        """Test default queue ordering."""
        sorts = QueueSortOptions.default_queue_order()
        assert len(sorts) == 2
        assert sorts[0].field == "priority"
        assert sorts[0].ascending is False
        assert sorts[1].field == "arrival_time"
        assert sorts[1].ascending is True


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_build_date_range_filter_both(self):
        """Test building date range filter with both dates."""
        from sqlalchemy import Column, DateTime
        
        field = Column("created_at", DateTime)
        from_date = datetime(2024, 1, 1)
        to_date = datetime(2024, 12, 31)
        
        conditions = build_date_range_filter(field, from_date, to_date)
        assert len(conditions) == 2
    
    def test_build_date_range_filter_from_only(self):
        """Test building date range filter with from_date only."""
        from sqlalchemy import Column, DateTime
        
        field = Column("created_at", DateTime)
        from_date = datetime(2024, 1, 1)
        
        conditions = build_date_range_filter(field, from_date=from_date)
        assert len(conditions) == 1
    
    def test_build_date_range_filter_to_only(self):
        """Test building date range filter with to_date only."""
        from sqlalchemy import Column, DateTime
        
        field = Column("created_at", DateTime)
        to_date = datetime(2024, 12, 31)
        
        conditions = build_date_range_filter(field, to_date=to_date)
        assert len(conditions) == 1
    
    def test_build_date_range_filter_none(self):
        """Test building date range filter with no dates."""
        from sqlalchemy import Column, DateTime
        
        field = Column("created_at", DateTime)
        
        conditions = build_date_range_filter(field)
        assert len(conditions) == 0
    
    def test_build_priority_range_filter_both(self):
        """Test building priority range filter with both values."""
        from sqlalchemy import Column, Integer
        
        field = Column("priority", Integer)
        
        conditions = build_priority_range_filter(field, min_priority=3, max_priority=8)
        assert len(conditions) == 2
    
    def test_build_priority_range_filter_min_only(self):
        """Test building priority range filter with min only."""
        from sqlalchemy import Column, Integer
        
        field = Column("priority", Integer)
        
        conditions = build_priority_range_filter(field, min_priority=3)
        assert len(conditions) == 1
    
    def test_build_priority_range_filter_max_only(self):
        """Test building priority range filter with max only."""
        from sqlalchemy import Column, Integer
        
        field = Column("priority", Integer)
        
        conditions = build_priority_range_filter(field, max_priority=8)
        assert len(conditions) == 1
    
    def test_build_priority_range_filter_none(self):
        """Test building priority range filter with no values."""
        from sqlalchemy import Column, Integer
        
        field = Column("priority", Integer)
        
        conditions = build_priority_range_filter(field)
        assert len(conditions) == 0
