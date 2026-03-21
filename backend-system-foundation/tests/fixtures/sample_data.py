"""Sample data fixtures for testing."""

from datetime import datetime, date, timedelta
from typing import Dict, Any
from uuid import uuid4


def sample_user_data(role: str = "nurse", **overrides) -> Dict[str, Any]:
    """
    Generate sample user data.
    
    Args:
        role: User role (nurse, doctor, admin)
        **overrides: Override default values
        
    Returns:
        Dict with user data
    """
    base_data = {
        "email": f"test_{role}_{uuid4().hex[:8]}@example.com",
        "password": "SecurePass123!@#",
        "first_name": "Test",
        "last_name": f"{role.capitalize()}",
        "is_active": True,
    }
    base_data.update(overrides)
    return base_data


def sample_patient_data(**overrides) -> Dict[str, Any]:
    """
    Generate sample patient data.
    
    Args:
        **overrides: Override default values
        
    Returns:
        Dict with patient data
    """
    base_data = {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": date(1980, 1, 15),
        "gender": "male",
        "contact_info": {
            "phone": "+1-555-0123",
            "email": "john.doe@example.com",
            "address": "123 Main St, City, State 12345"
        },
        "medical_history": {
            "allergies": ["penicillin"],
            "conditions": ["hypertension"],
            "medications": ["lisinopril 10mg"]
        }
    }
    base_data.update(overrides)
    return base_data


def sample_queue_entry_data(patient_id: str, **overrides) -> Dict[str, Any]:
    """
    Generate sample queue entry data.
    
    Args:
        patient_id: Patient UUID
        **overrides: Override default values
        
    Returns:
        Dict with queue entry data
    """
    base_data = {
        "patient_id": patient_id,
        "priority": 5,
        "status": "waiting",
        "symptoms": {
            "chief_complaint": "chest pain",
            "symptom_list": ["chest pain", "shortness of breath"],
            "duration": "2 hours"
        },
        "vital_signs": {
            "bp": "140/90",
            "hr": 95,
            "temp": 98.6,
            "spo2": 96,
            "resp_rate": 18
        },
        "arrival_time": datetime.utcnow()
    }
    base_data.update(overrides)
    return base_data


def sample_assignment_data(queue_entry_id: str, doctor_id: str, **overrides) -> Dict[str, Any]:
    """
    Generate sample assignment data.
    
    Args:
        queue_entry_id: Queue entry UUID
        doctor_id: Doctor user UUID
        **overrides: Override default values
        
    Returns:
        Dict with assignment data
    """
    base_data = {
        "queue_entry_id": queue_entry_id,
        "doctor_id": doctor_id,
        "assigned_at": datetime.utcnow(),
        "status": "active"
    }
    base_data.update(overrides)
    return base_data


# Sample data for multiple scenarios
SAMPLE_PATIENTS = [
    {
        "first_name": "Alice",
        "last_name": "Smith",
        "date_of_birth": date(1990, 5, 20),
        "gender": "female",
        "contact_info": {"phone": "+1-555-0001", "email": "alice@example.com"},
        "medical_history": {"allergies": [], "conditions": [], "medications": []}
    },
    {
        "first_name": "Bob",
        "last_name": "Johnson",
        "date_of_birth": date(1975, 8, 10),
        "gender": "male",
        "contact_info": {"phone": "+1-555-0002", "email": "bob@example.com"},
        "medical_history": {"allergies": ["latex"], "conditions": ["diabetes"], "medications": ["metformin"]}
    },
    {
        "first_name": "Carol",
        "last_name": "Williams",
        "date_of_birth": date(1985, 12, 3),
        "gender": "female",
        "contact_info": {"phone": "+1-555-0003", "email": "carol@example.com"},
        "medical_history": {"allergies": ["peanuts"], "conditions": ["asthma"], "medications": ["albuterol"]}
    }
]


SAMPLE_QUEUE_PRIORITIES = [
    {"priority": 10, "symptoms": {"chief_complaint": "cardiac arrest"}},
    {"priority": 8, "symptoms": {"chief_complaint": "severe bleeding"}},
    {"priority": 5, "symptoms": {"chief_complaint": "chest pain"}},
    {"priority": 3, "symptoms": {"chief_complaint": "minor laceration"}},
    {"priority": 1, "symptoms": {"chief_complaint": "cold symptoms"}}
]
