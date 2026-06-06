"""Seed script for sample patients."""

from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.patient import Patient


def seed_patients(db: Session) -> list[Patient]:
    """
    Seed sample patients into the database (idempotent).
    
    Creates diverse patient data with valid MRNs in format MRN-YYYYMMDD-XXXX.
    Patients represent various demographics and medical conditions.
    
    Args:
        db: Database session
        
    Returns:
        List of Patient objects
        
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    # Generate diverse patient data
    today = date.today()
    patients_data = [
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0001",
            "first_name": "Michael",
            "last_name": "Johnson",
            "date_of_birth": date(1985, 3, 15),
            "gender": "male",
            "contact_info": {
                "phone": "555-0101",
                "email": "michael.johnson@example.com",
                "address": "123 Main St, Springfield, IL 62701"
            },
            "medical_history": {
                "allergies": ["Penicillin"],
                "conditions": ["Hypertension"],
                "medications": ["Lisinopril 10mg daily"]
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0002",
            "first_name": "Sarah",
            "last_name": "Williams",
            "date_of_birth": date(1992, 7, 22),
            "gender": "female",
            "contact_info": {
                "phone": "555-0102",
                "email": "sarah.williams@example.com",
                "address": "456 Oak Ave, Springfield, IL 62702"
            },
            "medical_history": {
                "allergies": [],
                "conditions": ["Asthma"],
                "medications": ["Albuterol inhaler as needed"]
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0003",
            "first_name": "Robert",
            "last_name": "Davis",
            "date_of_birth": date(1978, 11, 8),
            "gender": "male",
            "contact_info": {
                "phone": "555-0103",
                "address": "789 Elm St, Springfield, IL 62703"
            },
            "medical_history": {
                "allergies": ["Sulfa drugs", "Latex"],
                "conditions": ["Type 2 Diabetes", "High cholesterol"],
                "medications": ["Metformin 500mg twice daily", "Atorvastatin 20mg daily"]
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0004",
            "first_name": "Emily",
            "last_name": "Martinez",
            "date_of_birth": date(2000, 5, 30),
            "gender": "female",
            "contact_info": {
                "phone": "555-0104",
                "email": "emily.martinez@example.com",
                "address": "321 Pine Rd, Springfield, IL 62704"
            },
            "medical_history": {
                "allergies": [],
                "conditions": [],
                "medications": []
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0005",
            "first_name": "James",
            "last_name": "Anderson",
            "date_of_birth": date(1965, 9, 12),
            "gender": "male",
            "contact_info": {
                "phone": "555-0105",
                "address": "654 Maple Dr, Springfield, IL 62705"
            },
            "medical_history": {
                "allergies": ["Aspirin"],
                "conditions": ["Coronary artery disease", "COPD"],
                "medications": [
                    "Clopidogrel 75mg daily",
                    "Tiotropium inhaler daily",
                    "Nitroglycerin sublingual as needed"
                ]
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0006",
            "first_name": "Maria",
            "last_name": "Garcia",
            "date_of_birth": date(1988, 2, 18),
            "gender": "female",
            "contact_info": {
                "phone": "555-0106",
                "email": "maria.garcia@example.com",
                "address": "987 Cedar Ln, Springfield, IL 62706"
            },
            "medical_history": {
                "allergies": [],
                "conditions": ["Migraine"],
                "medications": ["Sumatriptan 50mg as needed"]
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0007",
            "first_name": "David",
            "last_name": "Wilson",
            "date_of_birth": date(1995, 12, 5),
            "gender": "male",
            "contact_info": {
                "phone": "555-0107",
                "email": "david.wilson@example.com",
                "address": "147 Birch St, Springfield, IL 62707"
            },
            "medical_history": {
                "allergies": [],
                "conditions": [],
                "medications": []
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0008",
            "first_name": "Jennifer",
            "last_name": "Taylor",
            "date_of_birth": date(1972, 4, 25),
            "gender": "female",
            "contact_info": {
                "phone": "555-0108",
                "address": "258 Spruce Ave, Springfield, IL 62708"
            },
            "medical_history": {
                "allergies": ["Codeine"],
                "conditions": ["Hypothyroidism", "Osteoarthritis"],
                "medications": ["Levothyroxine 100mcg daily", "Ibuprofen 400mg as needed"]
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0009",
            "first_name": "Christopher",
            "last_name": "Brown",
            "date_of_birth": date(1990, 8, 14),
            "gender": "male",
            "contact_info": {
                "phone": "555-0109",
                "email": "chris.brown@example.com",
                "address": "369 Willow Way, Springfield, IL 62709"
            },
            "medical_history": {
                "allergies": [],
                "conditions": ["Anxiety disorder"],
                "medications": ["Sertraline 50mg daily"]
            }
        },
        {
            "mrn": f"MRN-{today.strftime('%Y%m%d')}-0010",
            "first_name": "Patricia",
            "last_name": "Moore",
            "date_of_birth": date(1958, 6, 3),
            "gender": "female",
            "contact_info": {
                "phone": "555-0110",
                "email": "patricia.moore@example.com",
                "address": "741 Ash Blvd, Springfield, IL 62710"
            },
            "medical_history": {
                "allergies": ["Shellfish"],
                "conditions": ["Rheumatoid arthritis", "Osteoporosis"],
                "medications": [
                    "Methotrexate 15mg weekly",
                    "Folic acid 1mg daily",
                    "Alendronate 70mg weekly"
                ]
            }
        }
    ]
    
    patients = []
    created_count = 0
    existing_count = 0
    
    for patient_data in patients_data:
        # Check if patient already exists
        existing_patient = db.query(Patient).filter(Patient.mrn == patient_data["mrn"]).first()
        
        if existing_patient:
            patients.append(existing_patient)
            existing_count += 1
        else:
            # Create new patient
            patient = Patient(**patient_data)
            db.add(patient)
            try:
                db.commit()
                db.refresh(patient)
                patients.append(patient)
                created_count += 1
            except IntegrityError:
                db.rollback()
                # Race condition: another process created it
                existing_patient = db.query(Patient).filter(Patient.mrn == patient_data["mrn"]).first()
                if existing_patient:
                    patients.append(existing_patient)
                    existing_count += 1
    
    print(f"✓ Patients: {created_count} created, {existing_count} already existed")
    return patients
