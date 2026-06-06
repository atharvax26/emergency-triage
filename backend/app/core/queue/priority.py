"""Priority calculation logic for queue management.

This module provides the foundation for priority-based queue ordering.
Phase 1: Simple manual priority (1-10)
Phase 3: Will integrate ML-based severity scoring

Requirements: 6.1, 6.3, 20.1
"""

from typing import Dict, Any


def calculate_priority(patient_data: Dict[str, Any]) -> int:
    """
    Calculate priority for a queue entry.
    
    Phase 1: Returns the manually provided priority value.
    Phase 3: Will integrate ML severity scoring model.
    
    Priority range: 1-10 (higher = more urgent)
    Queue ordering: critical (9-10) → high (7-8) → medium (4-6) → low (1-3)
    
    Args:
        patient_data: Dictionary containing patient information and priority
        
    Returns:
        Priority value (1-10)
        
    Requirements: 6.1, 20.1
    """
    # Phase 1: Simple manual priority
    # Hook for Phase 3: priority = ml_model.predict(patient_data)
    return patient_data.get("priority", 5)


def get_priority_category(priority: int) -> str:
    """
    Get the priority category name for a given priority value.
    
    Categories:
    - critical: 9-10
    - high: 7-8
    - medium: 4-6
    - low: 1-3
    
    Args:
        priority: Priority value (1-10)
        
    Returns:
        Priority category name
        
    Requirements: 6.3
    """
    if priority >= 9:
        return "critical"
    elif priority >= 7:
        return "high"
    elif priority >= 4:
        return "medium"
    else:
        return "low"


def compare_queue_entries(entry_a: Dict[str, Any], entry_b: Dict[str, Any]) -> int:
    """
    Compare two queue entries for ordering.
    
    Ordering rules:
    1. Higher priority comes first
    2. Within same priority, FIFO (earlier arrival_time comes first)
    
    Args:
        entry_a: First queue entry
        entry_b: Second queue entry
        
    Returns:
        -1 if entry_a should come before entry_b
        1 if entry_b should come before entry_a
        0 if they are equal
        
    Requirements: 6.3
    Property 17: Queue Priority Ordering
    """
    priority_a = entry_a.get("priority", 0)
    priority_b = entry_b.get("priority", 0)
    
    # Higher priority comes first
    if priority_a > priority_b:
        return -1
    elif priority_a < priority_b:
        return 1
    
    # Same priority: FIFO by arrival_time
    arrival_a = entry_a.get("arrival_time")
    arrival_b = entry_b.get("arrival_time")
    
    if arrival_a is None or arrival_b is None:
        return 0
    
    if arrival_a < arrival_b:
        return -1
    elif arrival_a > arrival_b:
        return 1
    
    return 0
