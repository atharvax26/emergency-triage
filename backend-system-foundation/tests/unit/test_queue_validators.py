"""Unit tests for queue validators."""

import pytest
from app.core.queue.validators import (
    validate_priority,
    validate_status,
    validate_status_transition,
    validate_symptoms,
    validate_vital_signs,
    validate_queue_entry_data,
)


class TestPriorityValidation:
    """Test priority validation."""
    
    def test_valid_priority(self):
        """Test valid priority values."""
        for priority in range(1, 11):
            is_valid, error = validate_priority(priority)
            assert is_valid is True
            assert error is None
    
    def test_priority_below_minimum(self):
        """Test priority below minimum."""
        is_valid, error = validate_priority(0)
        assert is_valid is False
        assert "between 1 and 10" in error
    
    def test_priority_above_maximum(self):
        """Test priority above maximum."""
        is_valid, error = validate_priority(11)
        assert is_valid is False
        assert "between 1 and 10" in error
    
    def test_priority_not_integer(self):
        """Test priority is not an integer."""
        is_valid, error = validate_priority("5")
        assert is_valid is False
        assert "must be an integer" in error


class TestStatusValidation:
    """Test status validation."""
    
    def test_valid_statuses(self):
        """Test all valid statuses."""
        valid_statuses = ["waiting", "assigned", "in_progress", "completed", "cancelled"]
        for status in valid_statuses:
            is_valid, error = validate_status(status)
            assert is_valid is True
            assert error is None
    
    def test_invalid_status(self):
        """Test invalid status."""
        is_valid, error = validate_status("invalid")
        assert is_valid is False
        assert "must be one of" in error
    
    def test_status_not_string(self):
        """Test status is not a string."""
        is_valid, error = validate_status(123)
        assert is_valid is False
        assert "must be a string" in error


class TestStatusTransitionValidation:
    """Test status transition validation."""
    
    def test_waiting_to_assigned(self):
        """Test valid transition: waiting -> assigned."""
        is_valid, error = validate_status_transition("waiting", "assigned")
        assert is_valid is True
        assert error is None
    
    def test_assigned_to_in_progress(self):
        """Test valid transition: assigned -> in_progress."""
        is_valid, error = validate_status_transition("assigned", "in_progress")
        assert is_valid is True
        assert error is None
    
    def test_in_progress_to_completed(self):
        """Test valid transition: in_progress -> completed."""
        is_valid, error = validate_status_transition("in_progress", "completed")
        assert is_valid is True
        assert error is None
    
    def test_any_to_cancelled(self):
        """Test valid transition: any -> cancelled."""
        for status in ["waiting", "assigned", "in_progress"]:
            is_valid, error = validate_status_transition(status, "cancelled")
            assert is_valid is True
            assert error is None
    
    def test_invalid_transition_waiting_to_in_progress(self):
        """Test invalid transition: waiting -> in_progress."""
        is_valid, error = validate_status_transition("waiting", "in_progress")
        assert is_valid is False
        assert "Invalid status transition" in error
    
    def test_invalid_transition_from_completed(self):
        """Test invalid transition from completed (terminal state)."""
        is_valid, error = validate_status_transition("completed", "waiting")
        assert is_valid is False
        assert "terminal state" in error
    
    def test_same_status_is_valid(self):
        """Test transition to same status is valid."""
        is_valid, error = validate_status_transition("waiting", "waiting")
        assert is_valid is True
        assert error is None


class TestSymptomsValidation:
    """Test symptoms validation."""
    
    def test_valid_symptoms(self):
        """Test valid symptoms with chief_complaint."""
        symptoms = {
            "chief_complaint": "Chest pain",
            "symptom_list": ["pain", "shortness of breath"],
            "duration": "2 hours"
        }
        is_valid, error = validate_symptoms(symptoms)
        assert is_valid is True
        assert error is None
    
    def test_missing_chief_complaint(self):
        """Test symptoms missing chief_complaint."""
        symptoms = {"symptom_list": ["pain"]}
        is_valid, error = validate_symptoms(symptoms)
        assert is_valid is False
        assert "chief_complaint" in error
    
    def test_empty_chief_complaint(self):
        """Test symptoms with empty chief_complaint."""
        symptoms = {"chief_complaint": ""}
        is_valid, error = validate_symptoms(symptoms)
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_symptoms_not_dict(self):
        """Test symptoms is not a dictionary."""
        is_valid, error = validate_symptoms("symptoms")
        assert is_valid is False
        assert "must be a dictionary" in error


class TestVitalSignsValidation:
    """Test vital signs validation."""
    
    def test_none_vital_signs(self):
        """Test None vital signs (optional)."""
        is_valid, error = validate_vital_signs(None)
        assert is_valid is True
        assert error is None
    
    def test_valid_vital_signs(self):
        """Test valid vital signs."""
        vital_signs = {
            "hr": 80,
            "temp": 37.5,
            "spo2": 98,
            "resp_rate": 16,
            "bp": {"systolic": 120, "diastolic": 80}
        }
        is_valid, error = validate_vital_signs(vital_signs)
        assert is_valid is True
        assert error is None
    
    def test_invalid_heart_rate_low(self):
        """Test heart rate below minimum."""
        vital_signs = {"hr": 20}
        is_valid, error = validate_vital_signs(vital_signs)
        assert is_valid is False
        assert "Heart rate" in error
    
    def test_invalid_heart_rate_high(self):
        """Test heart rate above maximum."""
        vital_signs = {"hr": 300}
        is_valid, error = validate_vital_signs(vital_signs)
        assert is_valid is False
        assert "Heart rate" in error
    
    def test_invalid_temperature_low(self):
        """Test temperature below minimum."""
        vital_signs = {"temp": 30}
        is_valid, error = validate_vital_signs(vital_signs)
        assert is_valid is False
        assert "Temperature" in error
    
    def test_invalid_spo2_high(self):
        """Test oxygen saturation above maximum."""
        vital_signs = {"spo2": 105}
        is_valid, error = validate_vital_signs(vital_signs)
        assert is_valid is False
        assert "Oxygen saturation" in error
    
    def test_invalid_blood_pressure_structure(self):
        """Test blood pressure with invalid structure."""
        vital_signs = {"bp": {"systolic": 120}}
        is_valid, error = validate_vital_signs(vital_signs)
        assert is_valid is False
        assert "diastolic" in error
    
    def test_invalid_blood_pressure_values(self):
        """Test blood pressure with systolic <= diastolic."""
        vital_signs = {"bp": {"systolic": 80, "diastolic": 120}}
        is_valid, error = validate_vital_signs(vital_signs)
        assert is_valid is False
        assert "greater than diastolic" in error
    
    def test_vital_signs_not_dict(self):
        """Test vital signs is not a dictionary."""
        is_valid, error = validate_vital_signs("vital_signs")
        assert is_valid is False
        assert "must be a dictionary" in error


class TestQueueEntryDataValidation:
    """Test complete queue entry data validation."""
    
    def test_valid_queue_entry_data(self):
        """Test valid queue entry data."""
        symptoms = {"chief_complaint": "Chest pain"}
        vital_signs = {"hr": 80, "temp": 37.5}
        
        is_valid, errors = validate_queue_entry_data(
            priority=5,
            status="waiting",
            symptoms=symptoms,
            vital_signs=vital_signs
        )
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_multiple_validation_errors(self):
        """Test multiple validation errors."""
        symptoms = {}  # Missing chief_complaint
        vital_signs = {"hr": 300}  # Invalid heart rate
        
        is_valid, errors = validate_queue_entry_data(
            priority=15,  # Invalid priority
            status="invalid",  # Invalid status
            symptoms=symptoms,
            vital_signs=vital_signs
        )
        
        assert is_valid is False
        assert len(errors) == 4  # All validations should fail
