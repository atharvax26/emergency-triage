"""Unit tests for Patient model."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient


@pytest.mark.asyncio
async def test_patient_creation(db_session: AsyncSession):
    """Test creating a patient with valid data."""
    # Arrange
    patient_data = {
        "mrn": "MRN-20240101-0001",
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": date(1990, 1, 1),
        "gender": "male",
        "contact_info": {
            "phone": "+1234567890",
            "email": "john.doe@example.com",
            "address": "123 Main St, City, State 12345"
        },
        "medical_history": {
            "allergies": ["penicillin"],
            "conditions": ["hypertension"],
            "medications": ["lisinopril"]
        }
    }
    
    # Act
    patient = Patient(**patient_data)
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    
    # Assert
    assert patient.id is not None
    assert patient.mrn == "MRN-20240101-0001"
    assert patient.first_name == "John"
    assert patient.last_name == "Doe"
    assert patient.date_of_birth == date(1990, 1, 1)
    assert patient.gender == "male"
    assert patient.contact_info["phone"] == "+1234567890"
    assert patient.medical_history["allergies"] == ["penicillin"]
    assert patient.created_at is not None
    assert patient.updated_at is not None


@pytest.mark.asyncio
async def test_patient_full_name_property(db_session: AsyncSession):
    """Test patient full_name property."""
    # Arrange
    patient = Patient(
        mrn="MRN-20240101-0002",
        first_name="Jane",
        last_name="Smith",
        date_of_birth=date(1985, 5, 15),
        gender="female",
        contact_info={"phone": "+1234567890"}
    )
    
    # Act
    full_name = patient.full_name
    
    # Assert
    assert full_name == "Jane Smith"


@pytest.mark.asyncio
async def test_patient_without_medical_history(db_session: AsyncSession):
    """Test creating a patient without medical history (optional field)."""
    # Arrange
    patient_data = {
        "mrn": "MRN-20240101-0003",
        "first_name": "Bob",
        "last_name": "Johnson",
        "date_of_birth": date(2000, 12, 31),
        "gender": "other",
        "contact_info": {"email": "bob@example.com"}
    }
    
    # Act
    patient = Patient(**patient_data)
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    
    # Assert
    assert patient.id is not None
    assert patient.medical_history is None
    assert patient.contact_info["email"] == "bob@example.com"


@pytest.mark.asyncio
async def test_patient_repr(db_session: AsyncSession):
    """Test patient string representation."""
    # Arrange
    patient = Patient(
        mrn="MRN-20240101-0004",
        first_name="Alice",
        last_name="Williams",
        date_of_birth=date(1995, 3, 20),
        gender="female",
        contact_info={"phone": "+1234567890"}
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    
    # Act
    repr_str = repr(patient)
    
    # Assert
    assert "Patient" in repr_str
    assert "MRN-20240101-0004" in repr_str
    assert "Alice Williams" in repr_str


@pytest.mark.asyncio
async def test_patient_to_dict(db_session: AsyncSession):
    """Test converting patient to dictionary."""
    # Arrange
    patient = Patient(
        mrn="MRN-20240101-0005",
        first_name="Charlie",
        last_name="Brown",
        date_of_birth=date(1988, 7, 10),
        gender="male",
        contact_info={"phone": "+1234567890"}
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    
    # Act
    patient_dict = patient.to_dict()
    
    # Assert
    assert patient_dict["mrn"] == "MRN-20240101-0005"
    assert patient_dict["first_name"] == "Charlie"
    assert patient_dict["last_name"] == "Brown"
    assert "id" in patient_dict
    assert "created_at" in patient_dict
    assert "updated_at" in patient_dict
