# Database Seed Scripts

This directory contains seed scripts for populating the development database with test data.

## Overview

The seed scripts are **idempotent** - they can be run multiple times without creating duplicate data. Each script checks if data already exists before creating new records.

## Seed Scripts

### 1. `seed_roles.py`
Creates three system roles:
- **nurse**: Patient intake and basic queue viewing
- **doctor**: Full queue access, patient assignment, triage decisions
- **admin**: Full system access including user management and audit logs

### 2. `seed_permissions.py`
Implements the complete RBAC (Role-Based Access Control) matrix:

| Resource | Action | Nurse | Doctor | Admin |
|----------|--------|-------|--------|-------|
| Patient  | Create | ✓     | ✓      | ✓     |
| Patient  | Read   | ✓     | ✓      | ✓     |
| Patient  | Update | ✓     | ✓      | ✓     |
| Patient  | Delete | ✗     | ✗      | ✓     |
| Queue    | Create | ✓     | ✓      | ✓     |
| Queue    | Read   | ✓     | ✓      | ✓     |
| Queue    | Update | ✗     | ✓      | ✓     |
| Queue    | Assign | ✗     | ✓      | ✓     |
| Queue    | Delete | ✗     | ✓      | ✓     |
| User     | Create | ✗     | ✗      | ✓     |
| User     | Read   | ✗     | ✗      | ✓     |
| User     | Update | ✗     | ✗      | ✓     |
| User     | Delete | ✗     | ✗      | ✓     |
| Audit    | Read   | ✗     | ✗      | ✓     |
| Audit    | Export | ✗     | ✗      | ✓     |

### 3. `seed_users.py`
Creates one test user per role with known credentials:

| Role   | Email                  | Password            |
|--------|------------------------|---------------------|
| Nurse  | nurse@example.com      | NursePassword123!   |
| Doctor | doctor@example.com     | DoctorPassword123!  |
| Admin  | admin@example.com      | AdminPassword123!   |

All passwords meet complexity requirements:
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

### 4. `seed_patients.py`
Creates 10 sample patients with diverse demographics:
- Various ages (from 1958 to 2000)
- Different genders (male, female)
- Diverse medical histories (allergies, conditions, medications)
- Valid MRNs in format `MRN-YYYYMMDD-XXXX`
- Complete contact information

### 5. `seed_queue.py`
Creates 8 sample queue entries with:
- Various priorities (2-9, where higher = more urgent)
- Different statuses (waiting, assigned, in_progress)
- Realistic symptoms and vital signs
- Different arrival times

## Usage

### Run All Seeds

From the project root directory:

```bash
python seed_database.py
```

### Run Individual Seeds

```python
from app.database.session import SessionLocal
from app.database.seeds import seed_roles, seed_permissions

db = SessionLocal()
roles = seed_roles(db)
seed_permissions(db, roles)
db.close()
```

## Idempotency

All seed scripts are idempotent and handle:

1. **Existing Records**: Check if records exist before creating
2. **Race Conditions**: Handle concurrent execution with proper error handling
3. **Partial Failures**: Each seed script can be run independently
4. **Updates**: Existing records are not modified (except for missing role assignments)

## Requirements Validation

The seed scripts validate:
- ✓ MRN format (MRN-YYYYMMDD-XXXX)
- ✓ Date of birth in the past
- ✓ Gender values (male, female, other, unknown)
- ✓ Password complexity requirements
- ✓ Queue priority bounds (1-10)
- ✓ Queue status values
- ✓ One active queue entry per patient

## Testing

After seeding, you can test authentication:

```bash
# Test nurse login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "nurse@example.com", "password": "NursePassword123!"}'

# Test doctor login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "doctor@example.com", "password": "DoctorPassword123!"}'

# Test admin login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "AdminPassword123!"}'
```

## Security Notes

⚠️ **WARNING**: These seed scripts are for **development only**. Do not use in production:

- Test user passwords are publicly documented
- Sample patient data is fictional but should not be used in production
- MRN format uses current date which may conflict with real data

## Requirements Mapping

- **Requirement 2.1**: Role-based authorization (roles and permissions)
- **Requirement 1.6**: Password hashing with bcrypt
- **Requirement 14.1**: Password complexity validation
- **Requirement 4.1-4.5**: Patient data validation
- **Requirement 6.1-6.5**: Queue management validation
