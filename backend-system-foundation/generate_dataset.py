"""
Generate synthetic patient dataset for Scaledown compression evaluation.
Target: 150 cases with realistic clinical narratives (1500–4000 tokens each).
Distribution: CRITICAL 20%, HIGH 25%, MEDIUM 25%, LOW 30%
"""

import json
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)  # Deterministic generation


def generate_patient(severity: str, case_num: int) -> dict:
    """Generate a single synthetic patient case with rich clinical narrative."""
    
    # Severity-specific vital ranges
    vitals_ranges = {
        "CRITICAL": {
            "systolic_bp": (60, 85),
            "diastolic_bp": (35, 55),
            "heart_rate": (125, 180),
            "respiratory_rate": (26, 45),
            "temperature": (35.0, 35.5, 39.5, 41.0),  # hypothermia or high fever
            "spo2": (70, 88),
        },
        "HIGH": {
            "systolic_bp": (85, 95, 175, 200),
            "diastolic_bp": (55, 65, 105, 120),
            "heart_rate": (105, 125),
            "respiratory_rate": (22, 28),
            "temperature": (38.5, 39.5),
            "spo2": (88, 92),
        },
        "MEDIUM": {
            "systolic_bp": (95, 110, 150, 170),
            "diastolic_bp": (65, 75, 95, 105),
            "heart_rate": (90, 105),
            "respiratory_rate": (18, 22),
            "temperature": (37.8, 38.5),
            "spo2": (92, 94),
        },
        "LOW": {
            "systolic_bp": (110, 135),
            "diastolic_bp": (70, 85),
            "heart_rate": (60, 90),
            "respiratory_rate": (12, 18),
            "temperature": (36.5, 37.5),
            "spo2": (95, 100),
        },
    }
    
    vr = vitals_ranges[severity]
    
    # Generate vitals
    if len(vr["systolic_bp"]) == 4:
        systolic_bp = random.choice([
            random.randint(vr["systolic_bp"][0], vr["systolic_bp"][1]),
            random.randint(vr["systolic_bp"][2], vr["systolic_bp"][3])
        ])
    else:
        systolic_bp = random.randint(vr["systolic_bp"][0], vr["systolic_bp"][1])
    
    if len(vr["diastolic_bp"]) == 4:
        diastolic_bp = random.choice([
            random.randint(vr["diastolic_bp"][0], vr["diastolic_bp"][1]),
            random.randint(vr["diastolic_bp"][2], vr["diastolic_bp"][3])
        ])
    else:
        diastolic_bp = random.randint(vr["diastolic_bp"][0], vr["diastolic_bp"][1])
    
    if len(vr["temperature"]) == 4:
        temperature = round(random.choice([
            random.uniform(vr["temperature"][0], vr["temperature"][1]),
            random.uniform(vr["temperature"][2], vr["temperature"][3])
        ]), 1)
    else:
        temperature = round(random.uniform(vr["temperature"][0], vr["temperature"][1]), 1)
    
    vitals = {
        "systolic_bp": systolic_bp,
        "diastolic_bp": diastolic_bp,
        "heart_rate": random.randint(vr["heart_rate"][0], vr["heart_rate"][1]),
        "respiratory_rate": random.randint(vr["respiratory_rate"][0], vr["respiratory_rate"][1]),
        "temperature": temperature,
        "spo2": random.randint(vr["spo2"][0], vr["spo2"][1]),
    }
    
    # Age distribution
    age_ranges = {
        "CRITICAL": (55, 85),
        "HIGH": (45, 75),
        "MEDIUM": (30, 65),
        "LOW": (18, 50),
    }
    age = random.randint(*age_ranges[severity])
    
    # Symptoms by severity
    symptom_sets = {
        "CRITICAL": [
            ["severe chest pain", "shortness of breath", "diaphoresis", "nausea"],
            ["altered mental status", "severe hypotension", "cyanosis"],
            ["respiratory distress", "severe dyspnea", "accessory muscle use", "tripod positioning"],
            ["unresponsive", "seizure activity", "postictal state"],
            ["severe abdominal pain", "hematemesis", "melena", "syncope"],
        ],
        "HIGH": [
            ["chest pain", "dyspnea", "diaphoresis"],
            ["severe headache", "photophobia", "neck stiffness"],
            ["abdominal pain", "vomiting", "fever"],
            ["back pain", "hematuria", "dysuria"],
            ["palpitations", "lightheadedness", "near-syncope"],
        ],
        "MEDIUM": [
            ["abdominal pain", "nausea", "vomiting"],
            ["fever", "cough", "malaise"],
            ["headache", "dizziness", "fatigue"],
            ["chest discomfort", "mild dyspnea"],
            ["joint pain", "swelling", "limited mobility"],
        ],
        "LOW": [
            ["mild headache", "fatigue"],
            ["sore throat", "rhinorrhea", "mild cough"],
            ["minor laceration", "no active bleeding"],
            ["ankle sprain", "mild swelling"],
            ["rash", "pruritus", "no respiratory symptoms"],
        ],
    }
    symptoms = random.choice(symptom_sets[severity])
    
    # Chief complaint
    chief_complaints = {
        "CRITICAL": ["severe chest pain", "unresponsive", "respiratory failure", "cardiac arrest", "severe trauma"],
        "HIGH": ["chest pain", "severe headache", "abdominal pain", "back pain", "palpitations"],
        "MEDIUM": ["abdominal pain", "fever", "headache", "chest discomfort", "joint pain"],
        "LOW": ["headache", "sore throat", "minor injury", "ankle sprain", "rash"],
    }
    chief_complaint = random.choice(chief_complaints[severity])
    
    # Names
    first_names = ["John", "Mary", "James", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
                   "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                  "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas"]
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    
    gender = random.choice(["male", "female"])
    
    return {
        "case_id": f"{severity.lower()}-{case_num:03d}",
        "patient_id": str(uuid.uuid4()),
        "name": name,
        "age": age,
        "gender": gender,
        "chief_complaint": chief_complaint,
        "symptoms": symptoms,
        "vitals": vitals,
        "expected_severity": severity,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def main():
    """Generate 150 synthetic patient cases."""
    
    # Target distribution
    distribution = {
        "CRITICAL": 30,  # 20%
        "HIGH": 38,      # 25%
        "MEDIUM": 38,    # 25%
        "LOW": 44,       # 30%
    }
    
    dataset = []
    for severity, count in distribution.items():
        for i in range(1, count + 1):
            case = generate_patient(severity, i)
            dataset.append(case)
    
    # Shuffle to avoid ordering bias
    random.shuffle(dataset)
    
    # Save
    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_cases": len(dataset),
        "distribution": {k: v for k, v in distribution.items()},
        "cases": dataset,
    }
    
    with open("data/synthetic_dataset.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Generated {len(dataset)} synthetic patient cases")
    print(f"Distribution: {distribution}")
    print(f"Saved to data/synthetic_dataset.json")


if __name__ == "__main__":
    main()
