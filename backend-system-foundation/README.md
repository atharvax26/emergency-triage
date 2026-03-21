# Backend System Foundation

Production-grade backend infrastructure for an Emergency Triage AI System built with FastAPI, PostgreSQL, Redis, and SQLAlchemy.

## Features

- **JWT Authentication**: Secure token-based authentication with RS256 algorithm
- **Role-Based Access Control**: Three roles (nurse, doctor, admin) with granular permissions
- **High-Performance Caching**: Redis-based caching for sessions, patients, and queue data
- **Comprehensive Audit Logging**: All system actions logged for compliance
- **Database Connection Pooling**: Optimized PostgreSQL connections (5-20 pool size)
- **Rate Limiting**: 100 requests/minute per user, 1000/minute per IP
- **Health Check Endpoints**: Kubernetes-ready liveness and readiness probes
- **API Documentation**: Auto-generated OpenAPI (Swagger) and ReDoc documentation

## Architecture

The system follows a layered architecture:

- **API Layer**: FastAPI endpoints with automatic validation
- **Core Services**: Business logic (Auth, Patient Intake, Queue, Audit)
- **Data Layer**: SQLAlchemy models with async support
- **Cache Layer**: Redis for high-speed data access
- **Middleware**: Authentication, authorization, audit logging, rate limiting

## Prerequisites

### Option 1: Docker (Recommended)

- Docker 20.10+
- Docker Compose 2.0+

### Option 2: Local Development

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- pip or poetry for dependency management

## Installation

### 1. Clone the repository

```bash
cd backend-system-foundation
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Set up database

```bash
# Create database
createdb triage_db

# Run migrations
alembic upgrade head
```

### 6. Start Redis

```bash
redis-server
```

## Running the Application

### Option 1: Docker (Recommended)

The easiest way to run the entire stack (FastAPI + PostgreSQL + Redis):

**Linux/Mac:**
```bash
# Start all services
./docker-start.sh up

# View logs
./docker-start.sh logs

# Seed database
./docker-start.sh seed

# Stop services
./docker-start.sh down
```

**Windows:**
```powershell
# Start all services
.\docker-start.ps1 up

# View logs
.\docker-start.ps1 logs

# Seed database
.\docker-start.ps1 seed

# Stop services
.\docker-start.ps1 down
```

Or use Docker Compose directly:
```bash
docker compose up -d
docker compose logs -f
docker compose down
```

The application will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

See [DOCKER.md](DOCKER.md) for detailed Docker documentation.

### Option 2: Local Development

#### Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the application is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment (dev/staging/prod) | `dev` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | (change in production) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |

## Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback migration

```bash
alembic downgrade -1
```

## Testing

### Run all tests

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=app --cov-report=html
```

### Run specific test file

```bash
pytest tests/unit/test_auth.py
```

## Code Quality

### Format code

```bash
black app tests
isort app tests
```

### Lint code

```bash
flake8 app tests
pylint app
mypy app
```

## Project Structure

```
backend-system-foundation/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Business logic services
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── middleware/       # Custom middleware
│   ├── database/         # Database configuration
│   ├── cache/            # Redis cache layer
│   ├── utils/            # Utility functions
│   ├── config.py         # Configuration management
│   ├── dependencies.py   # Dependency injection
│   └── main.py           # FastAPI application
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Test fixtures
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── alembic.ini          # Alembic configuration
└── README.md            # This file
```

## Security

- Passwords hashed with bcrypt (cost factor 12)
- JWT tokens with RS256 algorithm
- Account lockout after 10 failed login attempts
- Rate limiting to prevent abuse
- SQL injection prevention via parameterized queries
- XSS prevention via output encoding
- TLS 1.3 for all connections (production)

## Performance

- API response time: < 100ms (p95)
- Database query time: < 50ms (p95)
- Cache hit rate: > 80%
- Connection pooling: 5-20 connections

## License

Proprietary - All rights reserved

## Support

For issues and questions, please contact the development team.
