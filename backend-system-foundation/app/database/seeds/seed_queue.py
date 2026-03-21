"""Seed script for sample queue entries."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.queue import QueueEntry
from app.models.patient import Patient


def seed_queue_entries(db: Session, patients: list[Patient]) -> list[QueueEntry]:
    """
    Seed sample queue entries into the database (idempotent).
    
    Creates queue entries with various priorities and statuses.
    Ensures only one active queue entry per patient.
    
    Queue entry statuses:
    - waiting: Patient is waiting to be seen
    - assigned: Patient has been assigned to a doctor
    - in_progress: Patient is currently being treated
    - completed: Patient treatment is complete
    - cancelled: Queue entry was cancelled
    
    Args:
        db: Database session
        patients: List of Patient objects to create queue entries for
        
    Returns:
        List of QueueEntry objects
        
    Requirements: 6.1, 6.2, 6.4, 6.5
    """
    if not patients:
        print("⚠ Warning: No patients available for queue entries")
        return []
    
    # Create diverse queue entries with different priorities and statuses
    now = datetime.utcnow()
    
    queue_data = [
        {
            "patient_index": 0,
            "priority": 9,
            "status": "waiting",
            "symptoms": {
                "chief_complaint": "Severe chest pain",
                "symptom_list": ["chest pain", "shortness of breath", "sweating"],
                "duration": "30 minutes"
            },
            "vital_signs": {
                "bp": "160/95",
                "hr": 110,
                "temp": 98.6,
                "spo2": 94,
                "resp_rate": 22
            },
            "arrival_time": now - timedelta(minutes=15)
        },
        {
            "patient_index": 1,
            "priority": 7,
            "status": "waiting",
            "symptoms": {
                "chief_complaint": "Severe asthma attack",
                "symptom_list": ["difficulty breathing", "wheezing", "chest tightness"],
                "duration": "1 hour"
            },
            "vital_signs": {
                "bp": "130/80",
                "hr": 95,
                "temp": 98.4,
                "spo2": 91,
                "resp_rate": 28
            },
            "arrival_time": now - timedelta(minutes=25)
        },
        {
            "patient_index": 2,
            "priority": 5,
            "status": "assigned",
            "symptoms": {
                "chief_complaint": "Abdominal pain",
                "symptom_list": ["abdominal pain", "nausea", "vomiting"],
                "duration": "4 hours"
            },
            "vital_signs": {
                "bp": "140/85",
                "hr": 88,
                "temp": 99.2,
                "spo2": 98,
                "resp_rate": 18
            },
            "arrival_time": now - timedelta(hours=1, minutes=10)
        },
        {
            "patient_index": 3,
            "priority": 3,
            "status": "waiting",
            "symptoms": {
                "chief_complaint": "Ankle sprain",
                "symptom_list": ["ankle pain", "swelling", "difficulty walking"],
                "duration": "2 hours"
            },
            "vital_signs": {
                "bp": "120/75",
                "hr": 75,
                "temp": 98.6,
                "spo2": 99,
                "resp_rate": 16
            },
            "arrival_time": now - timedelta(minutes=45)
        },
        {
            "patient_index": 4,
            "priority": 8,
            "status": "in_progress",
            "symptoms": {
                "chief_complaint": "Suspected stroke",
                "symptom_list": ["facial drooping", "arm weakness", "speech difficulty"],
                "duration": "20 minutes"
            },
            "vital_signs": {
                "bp": "180/100",
                "hr": 92,
                "temp": 98.8,
                "spo2": 96,
                "resp_rate": 20
            },
            "arrival_time": now - timedelta(hours=2)
        },
        {
            "patient_index": 5,
            "priority": 6,
            "status": "waiting",
            "symptoms": {
                "chief_complaint": "Severe migraine",
                "symptom_list": ["severe headache", "nausea", "light sensitivity"],
                "duration": "3 hours"
            },
            "vital_signs": {
                "bp": "135/82",
                "hr": 80,
                "temp": 98.5,
                "spo2": 98,
                "resp_rate": 16
            },
            "arrival_time": now - timedelta(minutes=30)
        },
        {
            "patient_index": 6,
            "priority": 4,
            "status": "waiting",
            "symptoms": {
                "chief_complaint": "Laceration requiring stitches",
                "symptom_list": ["deep cut on hand", "bleeding controlled"],
                "duration": "1 hour"
            },
            "vital_signs": {
                "bp": "125/78",
                "hr": 82,
                "temp": 98.6,
                "spo2": 99,
                "resp_rate": 16
            },
            "arrival_time": now - timedelta(minutes=20)
        },
        {
            "patient_index": 7,
            "priority": 2,
            "status": "waiting",
            "symptoms": {
                "chief_complaint": "Minor cold symptoms",
                "symptom_list": ["cough", "runny nose", "mild fever"],
                "duration": "3 days"
            },
            "vital_signs": {
                "bp": "118/72",
                "hr": 70,
                "temp": 99.8,
                "spo2": 98,
                "resp_rate": 14
            },
            "arrival_time": now - timedelta(minutes=10)
        }
    ]
    
    queue_entries = []
    created_count = 0
    existing_count = 0
    skipped_count = 0
    
    for entry_data in queue_data:
        patient_index = entry_data.pop("patient_index")
        
        if patient_index >= len(patients):
            skipped_count += 1
            continue
        
        patient = patients[patient_index]
        
        # Check if patient already has an active queue entry
        active_statuses = ["waiting", "assigned", "in_progress"]
        existing_entry = db.query(QueueEntry).filter(
            QueueEntry.patient_id == patient.id,
            QueueEntry.status.in_(active_statuses)
        ).first()
        
        if existing_entry:
            queue_entries.append(existing_entry)
            existing_count += 1
        else:
            # Create new queue entry
            queue_entry = QueueEntry(
                patient_id=patient.id,
                **entry_data
            )
            db.add(queue_entry)
            try:
                db.commit()
                db.refresh(queue_entry)
                queue_entries.append(queue_entry)
                created_count += 1
            except IntegrityError:
                db.rollback()
                # Race condition: another process created it
                existing_entry = db.query(QueueEntry).filter(
                    QueueEntry.patient_id == patient.id,
                    QueueEntry.status.in_(active_statuses)
                ).first()
                if existing_entry:
                    queue_entries.append(existing_entry)
                    existing_count += 1
    
    print(f"✓ Queue entries: {created_count} created, {existing_count} already existed, {skipped_count} skipped")
    return queue_entries
