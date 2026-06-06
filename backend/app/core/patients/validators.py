"""Patient data validation functions."""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.utils.exceptions import ValidationError


def validate_mrn_format(mrn: str) -> bool:
    """
    Validate MRN format: MRN-YYYYMMDD-XXXX.
    
    Args:
        mrn: Medical Record Number to validate
        
    Returns:
        True if valid format
        
    Raises:
        ValidationError: If MRN format is invalid
        
    Requirements: 4.2
    """
    pattern = r'^MRN-\d{8}-\d{4}$'
    if not re.match(pattern, mrn):
        raise ValidationError(
            message="MRN must follow format MRN-YYYYMMDD-XXXX",
            details={"field": "mrn"}
        )
    
    # Validate the date part is a valid date
    try:
        date_part = mrn.split('-')[1]
        year = int(date_part[:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        date(year, month, day)
    except (ValueError, IndexError):
        raise ValidationError(
            message="MRN contains invalid date",
            details={"field": "mrn"}
        )
    
    return True


def validate_date_of_birth(dob: date) -> bool:
    """
    Validate date of birth is in the past.
    
    Args:
        dob: Date of birth to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If date is not in the past
        
    Requirements: 4.4
    """
    if dob >= date.today():
        raise ValidationError(
            message="Date of birth must be in the past",
            details={"field": "date_of_birth"}
        )
    return True


def validate_gender(gender: str) -> bool:
    """
    Validate gender is one of allowed values.
    
    Args:
        gender: Gender value to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If gender is not in allowed values
        
    Requirements: 4.5
    """
    allowed_genders = {'male', 'female', 'other', 'unknown'}
    if gender.lower() not in allowed_genders:
        raise ValidationError(
            message=f"Gender must be one of: {', '.join(allowed_genders)}",
            details={"field": "gender"}
        )
    return True


def validate_contact_info(contact_info: Dict[str, Any]) -> bool:
    """
    Validate contact_info structure contains at least one contact method.
    
    Args:
        contact_info: Contact information dictionary
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If contact_info is invalid
        
    Requirements: 4.7
    """
    if not isinstance(contact_info, dict):
        raise ValidationError(
            message="Contact info must be a dictionary",
            details={"field": "contact_info"}
        )
    
    # Must contain at least one contact method
    valid_methods = {'phone', 'email', 'address'}
    has_contact = any(
        key in contact_info and contact_info[key]
        for key in valid_methods
    )
    
    if not has_contact:
        raise ValidationError(
            message="Contact info must contain at least one contact method (phone, email, or address)",
            details={"field": "contact_info"}
        )
    
    # Validate email format if provided
    if 'email' in contact_info and contact_info['email']:
        email = contact_info['email']
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(
                message="Invalid email format",
                details={"field": "contact_info.email"}
            )
    
    # Validate phone format if provided (basic validation)
    if 'phone' in contact_info and contact_info['phone']:
        phone = str(contact_info['phone'])
        # Remove common separators
        phone_digits = re.sub(r'[\s\-\(\)\+]', '', phone)
        if not phone_digits.isdigit() or len(phone_digits) < 10:
            raise ValidationError(
                message="Invalid phone number format",
                details={"field": "contact_info.phone"}
            )
    
    return True


def validate_medical_history(medical_history: Optional[Dict[str, Any]]) -> bool:
    """
    Validate medical_history structure if provided.
    
    Args:
        medical_history: Medical history dictionary (optional)
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If medical_history structure is invalid
        
    Requirements: 4.7
    """
    if medical_history is None:
        return True
    
    if not isinstance(medical_history, dict):
        raise ValidationError(
            message="Medical history must be a dictionary",
            details={"field": "medical_history"}
        )
    
    # Validate structure if provided
    valid_keys = {'allergies', 'conditions', 'medications', 'notes'}
    
    # Check for unexpected keys (warning, not error)
    for key in medical_history.keys():
        if key not in valid_keys:
            # Allow additional keys but validate known ones
            pass
    
    # Validate allergies is a list if provided
    if 'allergies' in medical_history:
        if not isinstance(medical_history['allergies'], list):
            raise ValidationError(
                message="Allergies must be a list",
                details={"field": "medical_history.allergies"}
            )
    
    # Validate conditions is a list if provided
    if 'conditions' in medical_history:
        if not isinstance(medical_history['conditions'], list):
            raise ValidationError(
                message="Conditions must be a list",
                details={"field": "medical_history.conditions"}
            )
    
    # Validate medications is a list if provided
    if 'medications' in medical_history:
        if not isinstance(medical_history['medications'], list):
            raise ValidationError(
                message="Medications must be a list",
                details={"field": "medical_history.medications"}
            )
    
    return True


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    Validate that all required fields are present and non-empty.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Returns:
        True if all required fields are present
        
    Raises:
        ValidationError: If any required field is missing or empty
        
    Requirements: 4.1
    """
    missing_fields = []
    empty_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            empty_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            details={"field": "required_fields", "missing": missing_fields}
        )
    
    if empty_fields:
        raise ValidationError(
            message=f"Empty required fields: {', '.join(empty_fields)}",
            details={"field": "required_fields", "empty": empty_fields}
        )
    
    return True


def validate_patient_data(data: Dict[str, Any], is_update: bool = False) -> bool:
    """
    Validate complete patient data.
    
    Args:
        data: Patient data dictionary
        is_update: Whether this is an update operation (some fields optional)
        
    Returns:
        True if all validations pass
        
    Raises:
        ValidationError: If any validation fails
        
    Requirements: 4.1, 4.2, 4.4, 4.5, 4.7
    """
    # Required fields for creation
    if not is_update:
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'contact_info']
        validate_required_fields(data, required_fields)
    
    # Validate first_name length if provided
    if 'first_name' in data and data['first_name']:
        if len(data['first_name']) > 100:
            raise ValidationError(
                message="First name must not exceed 100 characters",
                details={"field": "first_name"}
            )
    
    # Validate last_name length if provided
    if 'last_name' in data and data['last_name']:
        if len(data['last_name']) > 100:
            raise ValidationError(
                message="Last name must not exceed 100 characters",
                details={"field": "last_name"}
            )
    
    # Validate date_of_birth if provided
    if 'date_of_birth' in data and data['date_of_birth']:
        dob = data['date_of_birth']
        if isinstance(dob, str):
            try:
                dob = datetime.fromisoformat(dob).date()
            except ValueError:
                raise ValidationError(
                    message="Invalid date format. Use ISO 8601 format (YYYY-MM-DD)",
                    details={"field": "date_of_birth"}
                )
        validate_date_of_birth(dob)
    
    # Validate gender if provided
    if 'gender' in data and data['gender']:
        validate_gender(data['gender'])
    
    # Validate contact_info if provided
    if 'contact_info' in data and data['contact_info']:
        validate_contact_info(data['contact_info'])
    
    # Validate medical_history if provided
    if 'medical_history' in data:
        validate_medical_history(data['medical_history'])
    
    # Validate MRN format if provided (for updates)
    if 'mrn' in data and data['mrn']:
        validate_mrn_format(data['mrn'])
    
    return True
