"""Queue validation functions for priority, status, and data structure validation."""

from typing import Any, Dict, List, Optional, Tuple


# Valid queue entry statuses
VALID_STATUSES = {"waiting", "assigned", "in_progress", "completed", "cancelled"}

# Valid status transitions (state machine)
VALID_TRANSITIONS = {
    "waiting": {"assigned", "cancelled"},
    "assigned": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),  # Terminal state
    "cancelled": set(),  # Terminal state
}

# Priority bounds
MIN_PRIORITY = 1
MAX_PRIORITY = 10


def validate_priority(priority: int) -> Tuple[bool, Optional[str]]:
    """
    Validate queue entry priority is within bounds (1-10).
    
    Args:
        priority: Priority value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Requirements: 6.1
    Property 15: Queue Priority Bounds
    """
    if not isinstance(priority, int):
        return False, "Priority must be an integer"
    
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        return False, f"Priority must be between {MIN_PRIORITY} and {MAX_PRIORITY}"
    
    return True, None


def validate_status(status: str) -> Tuple[bool, Optional[str]]:
    """
    Validate queue entry status is one of the allowed values.
    
    Args:
        status: Status value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Requirements: 6.4
    """
    if not isinstance(status, str):
        return False, "Status must be a string"
    
    if status not in VALID_STATUSES:
        return False, f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}"
    
    return True, None


def validate_status_transition(
    current_status: str, new_status: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate status transition follows the state machine rules.
    
    State machine:
    - waiting → assigned (when doctor assigned)
    - assigned → in_progress (when doctor starts treatment)
    - in_progress → completed (when treatment finished)
    - Any state → cancelled (manual cancellation)
    
    Args:
        current_status: Current status of the queue entry
        new_status: New status to transition to
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Requirements: 6.5
    Property 19: Valid Status Transitions
    """
    # Validate both statuses are valid
    is_valid, error = validate_status(current_status)
    if not is_valid:
        return False, f"Current status invalid: {error}"
    
    is_valid, error = validate_status(new_status)
    if not is_valid:
        return False, f"New status invalid: {error}"
    
    # If status is not changing, it's valid
    if current_status == new_status:
        return True, None
    
    # Check if transition is allowed
    allowed_transitions = VALID_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_transitions:
        return False, (
            f"Invalid status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(sorted(allowed_transitions)) if allowed_transitions else 'none (terminal state)'}"
        )
    
    return True, None


def validate_symptoms(symptoms: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate symptoms structure contains required fields.
    
    Args:
        symptoms: Symptoms dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Requirements: 6.1
    """
    if not isinstance(symptoms, dict):
        return False, "Symptoms must be a dictionary"
    
    # Must contain chief_complaint field
    if "chief_complaint" not in symptoms:
        return False, "Symptoms must contain 'chief_complaint' field"
    
    if not symptoms["chief_complaint"]:
        return False, "Chief complaint cannot be empty"
    
    return True, None


def validate_vital_signs(vital_signs: Optional[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Validate vital signs structure and medical ranges if provided.
    
    Optional fields with medical ranges:
    - bp (blood pressure): systolic/diastolic in mmHg
    - hr (heart rate): 30-250 bpm
    - temp (temperature): 35-42 Celsius
    - spo2 (oxygen saturation): 0-100%
    - resp_rate (respiratory rate): 5-60 breaths/min
    
    Args:
        vital_signs: Vital signs dictionary to validate (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Requirements: 6.1
    """
    # Vital signs are optional
    if vital_signs is None:
        return True, None
    
    if not isinstance(vital_signs, dict):
        return False, "Vital signs must be a dictionary"
    
    # Validate heart rate if provided
    if "hr" in vital_signs:
        hr = vital_signs["hr"]
        if not isinstance(hr, (int, float)):
            return False, "Heart rate must be a number"
        if hr < 30 or hr > 250:
            return False, "Heart rate must be between 30 and 250 bpm"
    
    # Validate temperature if provided
    if "temp" in vital_signs:
        temp = vital_signs["temp"]
        if not isinstance(temp, (int, float)):
            return False, "Temperature must be a number"
        if temp < 35 or temp > 42:
            return False, "Temperature must be between 35 and 42 Celsius"
    
    # Validate oxygen saturation if provided
    if "spo2" in vital_signs:
        spo2 = vital_signs["spo2"]
        if not isinstance(spo2, (int, float)):
            return False, "Oxygen saturation must be a number"
        if spo2 < 0 or spo2 > 100:
            return False, "Oxygen saturation must be between 0 and 100%"
    
    # Validate respiratory rate if provided
    if "resp_rate" in vital_signs:
        resp_rate = vital_signs["resp_rate"]
        if not isinstance(resp_rate, (int, float)):
            return False, "Respiratory rate must be a number"
        if resp_rate < 5 or resp_rate > 60:
            return False, "Respiratory rate must be between 5 and 60 breaths/min"
    
    # Validate blood pressure if provided
    if "bp" in vital_signs:
        bp = vital_signs["bp"]
        if not isinstance(bp, dict):
            return False, "Blood pressure must be a dictionary with 'systolic' and 'diastolic'"
        
        if "systolic" not in bp or "diastolic" not in bp:
            return False, "Blood pressure must contain 'systolic' and 'diastolic' values"
        
        systolic = bp["systolic"]
        diastolic = bp["diastolic"]
        
        if not isinstance(systolic, (int, float)) or not isinstance(diastolic, (int, float)):
            return False, "Blood pressure values must be numbers"
        
        if systolic < 50 or systolic > 250:
            return False, "Systolic blood pressure must be between 50 and 250 mmHg"
        
        if diastolic < 30 or diastolic > 150:
            return False, "Diastolic blood pressure must be between 30 and 150 mmHg"
        
        if systolic <= diastolic:
            return False, "Systolic blood pressure must be greater than diastolic"
    
    return True, None


def validate_queue_entry_data(
    priority: int,
    status: str,
    symptoms: Dict[str, Any],
    vital_signs: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate all queue entry data at once.
    
    Args:
        priority: Priority value (1-10)
        status: Status value
        symptoms: Symptoms dictionary
        vital_signs: Vital signs dictionary (optional)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
        
    Requirements: 6.1, 6.4, 6.5
    """
    errors = []
    
    # Validate priority
    is_valid, error = validate_priority(priority)
    if not is_valid:
        errors.append(error)
    
    # Validate status
    is_valid, error = validate_status(status)
    if not is_valid:
        errors.append(error)
    
    # Validate symptoms
    is_valid, error = validate_symptoms(symptoms)
    if not is_valid:
        errors.append(error)
    
    # Validate vital signs
    is_valid, error = validate_vital_signs(vital_signs)
    if not is_valid:
        errors.append(error)
    
    return len(errors) == 0, errors
