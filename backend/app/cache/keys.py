"""Cache key patterns for Redis."""

from uuid import UUID


class CacheKeys:
    """
    Cache key patterns for different resources.
    
    All keys follow the centralized pattern: cache:{domain}:{entity}:{id}
    This ensures consistency across all services and makes cache management easier.
    """

    # Session keys
    @staticmethod
    def session(token_hash: str) -> str:
        """Session cache key."""
        return f"cache:session:token:{token_hash}"

    @staticmethod
    def user_sessions(user_id: UUID) -> str:
        """User sessions list key."""
        return f"cache:session:user:{user_id}"

    @staticmethod
    def revoked_token(token_hash: str) -> str:
        """Revoked token key."""
        return f"cache:session:revoked:{token_hash}"

    # Patient keys
    @staticmethod
    def patient(patient_id: UUID) -> str:
        """Patient cache key."""
        return f"cache:patient:id:{patient_id}"

    @staticmethod
    def patient_by_mrn(mrn: str) -> str:
        """Patient by MRN cache key."""
        return f"cache:patient:mrn:{mrn}"

    # Queue keys
    @staticmethod
    def queue_entry(entry_id: UUID) -> str:
        """Queue entry cache key."""
        return f"cache:queue:entry:{entry_id}"

    @staticmethod
    def active_queue() -> str:
        """Active queue cache key."""
        return "cache:queue:active"

    @staticmethod
    def queue_stats() -> str:
        """Queue statistics cache key."""
        return "cache:queue:stats"

    # Permission keys
    @staticmethod
    def user_permissions(user_id: UUID) -> str:
        """User permissions cache key."""
        return f"cache:permissions:user:{user_id}"

    @staticmethod
    def user_roles(user_id: UUID) -> str:
        """User roles cache key."""
        return f"cache:permissions:roles:{user_id}"

    # Rate limiting keys
    @staticmethod
    def rate_limit_user(user_id: UUID) -> str:
        """Rate limit counter for user."""
        return f"cache:rate_limit:user:{user_id}"

    @staticmethod
    def rate_limit_ip(ip_address: str) -> str:
        """Rate limit counter for IP address."""
        return f"cache:rate_limit:ip:{ip_address}"

    # Account lockout keys
    @staticmethod
    def login_attempts(user_id: UUID) -> str:
        """Failed login attempts counter."""
        return f"cache:auth:login_attempts:{user_id}"

    @staticmethod
    def account_locked(user_id: UUID) -> str:
        """Account lockout flag."""
        return f"cache:auth:locked:{user_id}"

    # Idempotency keys
    @staticmethod
    def idempotency_key(operation_type: str, key: str) -> str:
        """Idempotency key for preventing duplicate operations."""
        return f"cache:idempotency:{operation_type}:{key}"
