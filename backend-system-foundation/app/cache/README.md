# Redis Caching Layer

Production-grade Redis caching implementation for the Emergency Triage AI System.

## Overview

The caching layer provides:
- **Centralized cache key patterns** following `cache:{domain}:{entity}:{id}` format
- **TTL management** with domain-specific expiration times
- **Cache invalidation** logic for data consistency
- **Graceful fallback** when Redis is unavailable
- **Connection pooling** for optimal performance

## Architecture

```
app/cache/
├── client.py       # Redis client with connection pooling
├── keys.py         # Centralized cache key patterns
├── service.py      # High-level cache service
└── README.md       # This file
```

## Cache Key Patterns

All cache keys follow the centralized pattern: `cache:{domain}:{entity}:{id}`

### Session Keys
- `cache:session:token:{token_hash}` - Session data
- `cache:session:user:{user_id}` - User sessions list
- `cache:session:revoked:{token_hash}` - Revoked tokens

### Patient Keys
- `cache:patient:id:{patient_id}` - Patient by ID
- `cache:patient:mrn:{mrn}` - Patient by MRN

### Queue Keys
- `cache:queue:entry:{entry_id}` - Queue entry
- `cache:queue:active` - Active queue state
- `cache:queue:stats` - Queue statistics

### Permission Keys
- `cache:permissions:user:{user_id}` - User permissions
- `cache:permissions:roles:{user_id}` - User roles

### Rate Limiting Keys
- `cache:rate_limit:user:{user_id}` - User rate limit counter
- `cache:rate_limit:ip:{ip_address}` - IP rate limit counter

### Auth Keys
- `cache:auth:login_attempts:{user_id}` - Failed login attempts
- `cache:auth:locked:{user_id}` - Account lockout flag

### Idempotency Keys
- `cache:idempotency:{operation_type}:{key}` - Idempotency protection

## TTL Strategy

| Domain | TTL | Use Case |
|--------|-----|----------|
| Session | 15 minutes | Auth tokens and session data |
| Patient | 5 minutes | Patient records |
| Queue | 1 minute | Queue state (high volatility) |
| Queue Stats | 30 seconds | Real-time statistics |
| Permission | 10 minutes | User permissions and roles |

## Usage Examples

### Basic Cache Operations

```python
from app.cache import CacheService, redis_client

# Initialize
cache_service = CacheService(redis_client)

# Session operations
await cache_service.set_session(token_hash, session_data)
session = await cache_service.get_session(token_hash)
await cache_service.delete_session(token_hash)

# Patient operations
await cache_service.set_patient(patient_id, patient_data)
patient = await cache_service.get_patient(patient_id)
await cache_service.invalidate_patient(patient_id, mrn)

# Queue operations
await cache_service.set_active_queue(queue_data)
queue = await cache_service.get_active_queue()
await cache_service.invalidate_queue()

# Permission operations
await cache_service.set_user_permissions(user_id, permissions)
perms = await cache_service.get_user_permissions(user_id)
await cache_service.invalidate_user_permissions(user_id)
```

### Cache Invalidation

Cache invalidation is automatic when data changes:

```python
# Patient update invalidates cache
await cache_service.invalidate_patient(patient_id, mrn)

# Queue update invalidates queue cache
await cache_service.invalidate_queue()

# Role change invalidates permission cache
await cache_service.invalidate_user_permissions(user_id)
```

### Rate Limiting

```python
# Increment rate limit counter
count = await cache_service.increment_rate_limit(user_id=user_id)

# Check if limit exceeded
if count > settings.RATE_LIMIT_PER_MINUTE:
    raise RateLimitExceeded()

# Get current count
current = await cache_service.get_rate_limit_count(user_id=user_id)
```

### Account Lockout

```python
# Track failed login attempts
attempts = await cache_service.increment_login_attempts(user_id)

# Lock account after threshold
if attempts >= settings.MAX_LOGIN_ATTEMPTS:
    await cache_service.lock_account(user_id)

# Check if account is locked
if await cache_service.is_account_locked(user_id):
    raise AccountLocked()

# Reset on successful login
await cache_service.reset_login_attempts(user_id)
```

### Idempotency Protection

```python
# Prevent duplicate operations
operation_type = "create_patient"
key = f"patient_{mrn}"

# Check if operation already in progress
if not await cache_service.check_idempotency(operation_type, key):
    raise DuplicateOperation()

try:
    # Perform operation
    patient = await create_patient(data)
finally:
    # Clear idempotency key after completion
    await cache_service.clear_idempotency(operation_type, key)
```

## Graceful Fallback

The cache layer is designed to fail gracefully when Redis is unavailable:

```python
# If Redis fails, operations return None/False instead of raising exceptions
session = await cache_service.get_session(token_hash)
# Returns None if Redis is down, application continues with DB fallback

set_result = await cache_service.set_session(token_hash, data)
# Returns False if Redis is down, application continues without caching
```

## Health Checks

```python
# Check Redis connectivity
health = await cache_service.health_check()

# Returns:
# {
#     "status": "healthy" | "unhealthy",
#     "connected": True | False,
#     "message": "Redis is operational" | "Redis connection failed"
# }
```

## Configuration

Cache settings are configured in `app/config.py`:

```python
# Redis connection
REDIS_URL = "redis://localhost:6379/0"
REDIS_MAX_CONNECTIONS = 50

# TTL settings (seconds)
CACHE_TTL_SESSION = 900      # 15 minutes
CACHE_TTL_PATIENT = 300      # 5 minutes
CACHE_TTL_QUEUE = 60         # 1 minute
CACHE_TTL_PERMISSION = 600   # 10 minutes

# Rate limiting
RATE_LIMIT_PER_MINUTE = 100
RATE_LIMIT_PER_IP_MINUTE = 1000

# Account lockout
MAX_LOGIN_ATTEMPTS = 10
ACCOUNT_LOCKOUT_MINUTES = 30
```

## Testing

### Unit Tests

```bash
pytest tests/unit/test_cache_service.py -v
```

### Integration Tests

```bash
# Requires Redis running
pytest tests/integration/test_cache_integration.py -v
```

## Performance Considerations

### Connection Pooling
- Max connections: 50 (configurable)
- Automatic connection reuse
- Graceful connection handling

### TTL Management
- Automatic expiration prevents stale data
- Domain-specific TTLs balance freshness vs. performance
- Short TTLs for volatile data (queue: 1 min)
- Longer TTLs for stable data (permissions: 10 min)

### Cache Invalidation
- Explicit invalidation on data updates
- Prevents cache inconsistency
- Minimal performance impact

## Best Practices

1. **Always use cache service methods** instead of direct Redis client calls
2. **Invalidate cache on updates** to maintain consistency
3. **Handle None returns** gracefully (cache miss or Redis failure)
4. **Use idempotency protection** for critical operations
5. **Monitor cache hit rates** to optimize TTL values
6. **Test with Redis unavailable** to ensure graceful degradation

## Monitoring

Key metrics to monitor:
- Cache hit rate (target: >80%)
- Redis connection pool usage
- Cache operation latency
- Failed cache operations (graceful fallbacks)
- TTL effectiveness per domain

## Future Enhancements

- Redis Cluster support for horizontal scaling
- Cache warming strategies
- Advanced eviction policies
- Distributed locking for critical sections
- Cache analytics and optimization
