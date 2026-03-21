"""Integration tests for queue API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.patient import Patient
from app.models.queue import QueueEntry
from app.models.user import User


@pytest.mark.integration
@pytest.mark.asyncio
class TestQueueEndpoints:
    """Test queue API endpoints."""
    
    async def test_add_patient_to_queue(
        self,
        client: AsyncClient,
        sample_patient: Patient,
        nurse_auth_headers: dict
    ):
        """Test adding patient to queue."""
        response = await client.post(
            "/api/v1/queue",
            json={
                "patient_id": str(sample_patient.id),
                "priority": 5,
                "symptoms": {
                    "chief_complaint": "chest pain",
                    "symptom_list": ["chest pain"],
                    "duration": "2 hours"
                },
                "vital_signs": {
                    "bp": "140/90",
                    "hr": 95,
                    "temp": 98.6,
                    "spo2": 96,
                    "resp_rate": 18
                }
            },
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == str(sample_patient.id)
        assert data["priority"] == 5
        assert data["status"] == "waiting"
    
    async def test_add_duplicate_queue_entry_fails(
        self,
        client: AsyncClient,
        sample_queue_entry: QueueEntry,
        nurse_auth_headers: dict
    ):
        """Test adding patient already in queue returns 409."""
        response = await client.post(
            "/api/v1/queue",
            json={
                "patient_id": str(sample_queue_entry.patient_id),
                "priority": 5,
                "symptoms": {"chief_complaint": "test"}
            },
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 409
    
    async def test_get_queue_ordered_by_priority(
        self,
        client: AsyncClient,
        sample_queue_entries: list[QueueEntry],
        nurse_auth_headers: dict
    ):
        """Test queue is ordered by priority (highest first)."""
        response = await client.get(
            "/api/v1/queue",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        
        # Verify descending priority order
        priorities = [item["priority"] for item in items]
        assert priorities == sorted(priorities, reverse=True)
    
    async def test_get_queue_entry(
        self,
        client: AsyncClient,
        sample_queue_entry: QueueEntry,
        nurse_auth_headers: dict
    ):
        """Test getting queue entry by ID."""
        response = await client.get(
            f"/api/v1/queue/{sample_queue_entry.id}",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_queue_entry.id)
        assert data["priority"] == sample_queue_entry.priority
    
    async def test_update_queue_priority_as_doctor(
        self,
        client: AsyncClient,
        sample_queue_entry: QueueEntry,
        doctor_auth_headers: dict
    ):
        """Test doctor can update queue priority."""
        response = await client.put(
            f"/api/v1/queue/{sample_queue_entry.id}",
            json={"priority": 8},
            headers=doctor_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 8
    
    async def test_update_queue_priority_as_nurse_fails(
        self,
        client: AsyncClient,
        sample_queue_entry: QueueEntry,
        nurse_auth_headers: dict
    ):
        """Test nurse cannot update queue priority."""
        response = await client.put(
            f"/api/v1/queue/{sample_queue_entry.id}",
            json={"priority": 8},
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 403
    
    async def test_assign_patient_to_doctor(
        self,
        client: AsyncClient,
        sample_queue_entry: QueueEntry,
        doctor_user: User,
        doctor_auth_headers: dict
    ):
        """Test assigning patient to doctor."""
        response = await client.post(
            f"/api/v1/queue/{sample_queue_entry.id}/assign",
            json={"doctor_id": str(doctor_user.id)},
            headers=doctor_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["doctor_id"] == str(doctor_user.id)
        assert data["status"] == "active"
    
    async def test_assign_patient_as_nurse_fails(
        self,
        client: AsyncClient,
        sample_queue_entry: QueueEntry,
        doctor_user: User,
        nurse_auth_headers: dict
    ):
        """Test nurse cannot assign patients."""
        response = await client.post(
            f"/api/v1/queue/{sample_queue_entry.id}/assign",
            json={"doctor_id": str(doctor_user.id)},
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 403
    
    async def test_remove_from_queue_as_doctor(
        self,
        client: AsyncClient,
        sample_queue_entry: QueueEntry,
        doctor_auth_headers: dict
    ):
        """Test doctor can remove entry from queue."""
        response = await client.delete(
            f"/api/v1/queue/{sample_queue_entry.id}",
            headers=doctor_auth_headers
        )
        
        assert response.status_code == 200
    
    async def test_get_queue_statistics(
        self,
        client: AsyncClient,
        sample_queue_entries: list[QueueEntry],
        doctor_auth_headers: dict
    ):
        """Test getting queue statistics."""
        response = await client.get(
            "/api/v1/queue/stats",
            headers=doctor_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "by_status" in data
        assert "by_priority" in data
    
    async def test_filter_queue_by_status(
        self,
        client: AsyncClient,
        sample_queue_entries: list[QueueEntry],
        nurse_auth_headers: dict
    ):
        """Test filtering queue by status."""
        response = await client.get(
            "/api/v1/queue?status=waiting",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "waiting" for item in data["items"])
    
    async def test_filter_queue_by_priority_range(
        self,
        client: AsyncClient,
        sample_queue_entries: list[QueueEntry],
        nurse_auth_headers: dict
    ):
        """Test filtering queue by priority range."""
        response = await client.get(
            "/api/v1/queue?min_priority=5&max_priority=10",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(5 <= item["priority"] <= 10 for item in data["items"])
