# Database Migrations

This directory contains Alembic database migrations for the Backend System Foundation.

## Overview

The migrations are organized in sequential order:

1. **001_initial_schema.py** - Creates all database tables with proper constraints and indexes
2. **002_seed_roles_permissions.py** - Seeds initial roles and permissions based on RBAC matrix

## Database Schema

### Tables Created

1. **users** - System users (nurses, doctors, admins)
2. **roles** - User roles (nurse, doctor, admin)
3. **permissions** - Role-based permissions
4. **user_roles** - User-role associations
5. **sessions** - Authentication sessions
6. **patients** - Patient records
7. **queue_entries** - Emergency triage queue
8. **assignments** - Patient-doctor assignments
9. **audit_logs** - Audit trail records

### Seed Data

The migrations seed the following roles and permissions:

#### Roles

- **nurse**: Nurse role for patient intake and basic queue viewing
- **doctor**: Doctor role for full queue access, patient assignment, and triage decisions
- **admin**: Administrator role for user management, system configuration, and audit access

#### Permissions (RBAC Matrix)

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

## Prerequisites

1. PostgreSQL 15+ running and accessible
2. Database created (default: `triage_db`)
3. Environment variables configured in `.env` file

## Usage

### Apply All Migrations

```bash
# Upgrade to the latest version
alembic upgrade head
```

### Revert Migrations

```bash
# Revert one migration
alembic downgrade -1

# Revert all migrations
alembic downgrade base

# Revert to specific revision
alembic downgrade 001
```

### Check Migration Status

```bash
# Show current migration version
alembic current

# Show migration history
alembic history

# Show migration history with details
alembic history --verbose
```

### Create New Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration template
alembic revision -m "description of changes"
```

## Testing Migrations

### Validate Migration Files

```bash
# Run validation script
python test_migrations.py
```

### Test Migration Flow

```bash
# Run migration flow test
python test_migration_flow.py
```

### Manual Testing

```bash
# Apply migrations
alembic upgrade head

# Verify tables were created
psql -U postgres -d triage_db -c "\dt"

# Verify seed data
psql -U postgres -d triage_db -c "SELECT * FROM roles;"
psql -U postgres -d triage_db -c "SELECT * FROM permissions;"

# Revert migrations
alembic downgrade base

# Verify tables were dropped
psql -U postgres -d triage_db -c "\dt"
```

## Migration Structure

Each migration file contains:

- **revision**: Unique identifier for this migration
- **down_revision**: Previous migration in the chain (None for first migration)
- **upgrade()**: Function to apply the migration
- **downgrade()**: Function to revert the migration

Example:

```python
"""Description of migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""

revision = '001'
down_revision = None

def upgrade() -> None:
    """Apply migration changes."""
    # Create tables, add columns, etc.
    pass

def downgrade() -> None:
    """Revert migration changes."""
    # Drop tables, remove columns, etc.
    pass
```

## Best Practices

1. **Always test migrations** in development before applying to production
2. **Backup database** before running migrations in production
3. **Review auto-generated migrations** - they may need manual adjustments
4. **Keep migrations small** - one logical change per migration
5. **Never modify existing migrations** - create new ones instead
6. **Test both upgrade and downgrade** paths
7. **Use transactions** - migrations run in transactions by default

## Troubleshooting

### Migration fails with "relation already exists"

The table already exists in the database. Either:
- Drop the table manually: `DROP TABLE table_name CASCADE;`
- Revert to a previous migration: `alembic downgrade -1`
- Mark migration as applied: `alembic stamp head`

### Migration fails with "column does not exist"

The database schema is out of sync. Either:
- Revert all migrations: `alembic downgrade base`
- Apply migrations from scratch: `alembic upgrade head`

### Cannot connect to database

Check your `.env` file and ensure:
- `DATABASE_URL` is correct
- PostgreSQL is running
- Database exists
- User has proper permissions

### Alembic version table not found

Initialize Alembic:
```bash
alembic stamp head
```

## Requirements Validation

These migrations satisfy the following requirements:

- **Requirement 2.1**: Role-Based Authorization - Seeds roles and permissions
- **Requirement 13.1**: Database Schema and Relationships - Creates all tables with proper constraints
- **Requirement 13.2**: Enforces foreign key constraints, unique constraints, and indexes

## Related Files

- `env.py` - Alembic environment configuration
- `script.py.mako` - Template for new migrations
- `../../alembic.ini` - Alembic configuration file
- `../base.py` - SQLAlchemy declarative base
- `../session.py` - Database session management
- `../../models/` - SQLAlchemy model definitions
