"""Integration tests for patient API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from tests.fixtures.sample_data import sample_patient_data


@pytest.mark.integration
@pytest.mark.asyncio
class TestPatientEndpoints:
    """Test patient API endpoints."""
    
    async def test_create_patient_as_nurse(
        self,
        client: AsyncClient,
        nurse_auth_headers: dict
    ):
        """Test nurse can create patient."""
        patient_data = sample_patient_data()
        
        response = await client.post(
            "/api/v1/patients",
            json={
                "first_name": patient_data["first_name"],
                "last_name": patient_data["last_name"],
                "date_of_birth": patient_data["date_of_birth"].isoformat(),
                "gender": patient_data["gender"],
                "contact_info": patient_data["contact_info"],
                "medical_history": patient_data["medical_history"]
            },
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == patient_data["first_name"]
        assert data["last_name"] == patient_data["last_name"]
        assert "mrn" in data
        assert data["mrn"].startswith("MRN-")
    
    async def test_create_patient_unauthorized(self, client: AsyncClient):
        """Test creating patient without auth returns 401."""
        patient_data = sample_patient_data()
        
        response = await client.post(
            "/api/v1/patients",
            json={
                "first_name": patient_data["first_name"],
                "last_name": patient_data["last_name"],
                "date_of_birth": patient_data["date_of_birth"].isoformat(),
                "gender": patient_data["gender"]
            }
        )
        
        assert response.status_code == 401
    
    async def test_get_patient(
        self,
        client: AsyncClient,
        sample_patient: Patient,
        nurse_auth_headers: dict
    ):
        """Test getting patient by ID."""
        response = await client.get(
            f"/api/v1/patients/{sample_patient.id}",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_patient.id)
        assert data["mrn"] == sample_patient.mrn
    
    async def test_get_patient_not_found(
        self,
        client: AsyncClient,
        nurse_auth_headers: dict
    ):
        """Test getting non-existent patient returns 404."""
        from uuid import uuid4
        
        response = await client.get(
            f"/api/v1/patients/{uuid4()}",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_update_patient(
        self,
        client: AsyncClient,
        sample_patient: Patient,
        nurse_auth_headers: dict
    ):
        """Test updating patient."""
        response = await client.put(
            f"/api/v1/patients/{sample_patient.id}",
            json={
                "first_name": "Updated",
                "last_name": sample_patient.last_name
            },
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        # MRN should remain unchanged
        assert data["mrn"] == sample_patient.mrn
    
    async def test_list_patients(
        self,
        client: AsyncClient,
        sample_patients: list[Patient],
        nurse_auth_headers: dict
    ):
        """Test listing patients with pagination."""
        response = await client.get(
            "/api/v1/patients?page=1&page_size=10",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert len(data["items"]) <= 10
    
    async def test_search_patients_by_name(
        self,
        client: AsyncClient,
        sample_patients: list[Patient],
        nurse_auth_headers: dict
    ):
        """Test searching patients by name."""
        response = await client.get(
            "/api/v1/patients/search?first_name=Alice",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert any(p["first_name"] == "Alice" for p in data["items"])
    
    async def test_search_patients_case_insensitive(
        self,
        client: AsyncClient,
        sample_patients: list[Patient],
        nurse_auth_headers: dict
    ):
        """Test patient search is case-insensitive."""
        response = await client.get(
            "/api/v1/patients/search?first_name=alice",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert any(p["first_name"].lower() == "alice" for p in data["items"])
