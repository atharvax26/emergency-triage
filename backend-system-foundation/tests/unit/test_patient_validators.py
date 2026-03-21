"""Unit tests for patient validators."""

import pytest
from datetime import date, timedelta

from app.core.patients.validators import (
    validate_mrn_format,
    validate_date_of_birth,
    validate_gender,
    validate_contact_info,
    validate_medical_history,
    validate_required_fields,
    validate_patient_data
)
from app.utils.exceptions import ValidationError


class TestMRNValidation:
    """Test MRN format validation."""
    
    def test_valid_mrn_format(self):
        """Test valid MRN format passes validation."""
        assert validate_mrn_format("MRN-20240101-0001") is True
        assert validate_mrn_format("MRN-20231231-9999") is True
    
    def test_invalid_mrn_format(self):
        """Test invalid MRN format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_mrn_format("INVALID-FORMAT")
        assert "MRN must follow format" in exc_info.value.message
        
        with pytest.raises(ValidationError):
            validate_mrn_format("MRN-2024-0001")  # Wrong date format
        
        with pytest.raises(ValidationError):
            validate_mrn_format("MRN-20240101-01")  # Wrong sequence length
    
    def test_invalid_date_in_mrn(self):
        """Test MRN with invalid date raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_mrn_format("MRN-20241301-0001")  # Invalid month
        assert "invalid date" in exc_info.value.message.lower()


class TestDateOfBirthValidation:
    """Test date of birth validation."""
    
    def test_valid_date_of_birth(self):
        """Test date in the past passes validation."""
        past_date = date.today() - timedelta(days=365)
        assert validate_date_of_birth(past_date) is True
    
    def test_today_date_fails(self):
        """Test today's date fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_of_birth(date.today())
        assert "must be in the past" in exc_info.value.message
    
    def test_future_date_fails(self):
        """Test future date fails validation."""
        future_date = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            validate_date_of_birth(future_date)
        assert "must be in the past" in exc_info.value.message


class TestGenderValidation:
    """Test gender validation."""
    
    def test_valid_genders(self):
        """Test valid gender values pass validation."""
        assert validate_gender("male") is True
        assert validate_gender("female") is True
        assert validate_gender("other") is True
        assert validate_gender("unknown") is True
        assert validate_gender("MALE") is True  # Case insensitive
    
    def test_invalid_gender(self):
        """Test invalid gender value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_gender("invalid")
        assert "must be one of" in exc_info.value.message.lower()


class TestContactInfoValidation:
    """Test contact info validation."""
    
    def test_valid_contact_info_with_phone(self):
        """Test valid contact info with phone passes."""
        contact_info = {"phone": "1234567890"}
        assert validate_contact_info(contact_info) is True
    
    def test_valid_contact_info_with_email(self):
        """Test valid contact info with email passes."""
        contact_info = {"email": "test@example.com"}
        assert validate_contact_info(contact_info) is True
    
    def test_valid_contact_info_with_address(self):
        """Test valid contact info with address passes."""
        contact_info = {"address": "123 Main St"}
        assert validate_contact_info(contact_info) is True
    
    def test_empty_contact_info_fails(self):
        """Test empty contact info fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_contact_info({})
        assert "at least one contact method" in exc_info.value.message
    
    def test_invalid_email_format(self):
        """Test invalid email format fails validation."""
        contact_info = {"email": "invalid-email"}
        with pytest.raises(ValidationError) as exc_info:
            validate_contact_info(contact_info)
        assert "email format" in exc_info.value.message.lower()
    
    def test_invalid_phone_format(self):
        """Test invalid phone format fails validation."""
        contact_info = {"phone": "123"}  # Too short
        with pytest.raises(ValidationError) as exc_info:
            validate_contact_info(contact_info)
        assert "phone" in exc_info.value.message.lower()


class TestMedicalHistoryValidation:
    """Test medical history validation."""
    
    def test_none_medical_history_passes(self):
        """Test None medical history passes validation."""
        assert validate_medical_history(None) is True
    
    def test_valid_medical_history(self):
        """Test valid medical history structure passes."""
        medical_history = {
            "allergies": ["penicillin"],
            "conditions": ["diabetes"],
            "medications": ["insulin"]
        }
        assert validate_medical_history(medical_history) is True
    
    def test_invalid_allergies_type(self):
        """Test invalid allergies type fails validation."""
        medical_history = {"allergies": "not a list"}
        with pytest.raises(ValidationError) as exc_info:
            validate_medical_history(medical_history)
        assert "allergies must be a list" in exc_info.value.message.lower()


class TestRequiredFieldsValidation:
    """Test required fields validation."""
    
    def test_all_required_fields_present(self):
        """Test validation passes when all required fields present."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": date(1990, 1, 1)
        }
        required = ["first_name", "last_name", "date_of_birth"]
        assert validate_required_fields(data, required) is True
    
    def test_missing_required_field(self):
        """Test validation fails when required field missing."""
        data = {"first_name": "John"}
        required = ["first_name", "last_name"]
        with pytest.raises(ValidationError) as exc_info:
            validate_required_fields(data, required)
        assert "missing required fields" in exc_info.value.message.lower()
    
    def test_empty_required_field(self):
        """Test validation fails when required field is empty."""
        data = {"first_name": "John", "last_name": ""}
        required = ["first_name", "last_name"]
        with pytest.raises(ValidationError) as exc_info:
            validate_required_fields(data, required)
        assert "empty required fields" in exc_info.value.message.lower()


class TestPatientDataValidation:
    """Test complete patient data validation."""
    
    def test_valid_patient_data(self):
        """Test valid patient data passes validation."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": date(1990, 1, 1),
            "gender": "male",
            "contact_info": {"phone": "1234567890"}
        }
        assert validate_patient_data(data, is_update=False) is True
    
    def test_patient_data_with_medical_history(self):
        """Test patient data with medical history passes."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": date(1990, 1, 1),
            "gender": "male",
            "contact_info": {"email": "john@example.com"},
            "medical_history": {"allergies": ["penicillin"]}
        }
        assert validate_patient_data(data, is_update=False) is True
    
    def test_missing_required_fields_for_creation(self):
        """Test validation fails when required fields missing for creation."""
        data = {"first_name": "John"}
        with pytest.raises(ValidationError):
            validate_patient_data(data, is_update=False)
    
    def test_update_with_partial_data(self):
        """Test update validation allows partial data."""
        data = {"first_name": "Jane"}
        assert validate_patient_data(data, is_update=True) is True
    
    def test_name_length_validation(self):
        """Test name length validation."""
        data = {
            "first_name": "A" * 101,  # Too long
            "last_name": "Doe",
            "date_of_birth": date(1990, 1, 1),
            "gender": "male",
            "contact_info": {"phone": "1234567890"}
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_patient_data(data, is_update=False)
        assert "100 characters" in exc_info.value.message
