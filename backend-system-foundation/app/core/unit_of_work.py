"""Unit of Work pattern for transaction management.

This module implements the Unit of Work pattern to ensure atomic operations
across multiple database operations. It provides:
- Automatic transaction begin/commit/rollback
- Nested transaction support (SAVEPOINT)
- Context manager interface for clean resource management
- Integration with FastAPI dependency injection

Requirements: 19.4, 19.5
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import AsyncSessionLocal
from app.utils.exceptions import DatabaseError


class UnitOfWork:
    """
    Unit of Work pattern implementation for managing database transactions.
    
    Provides:
    - Single commit boundary for multiple operations
    - Automatic rollback on failure
    - Nested transaction support via SAVEPOINT
    - Idempotent retry safety
    
    Usage:
        async with UnitOfWork() as uow:
            # Perform multiple database operations
            user = User(...)
            uow.session.add(user)
            
            patient = Patient(...)
            uow.session.add(patient)
            
            # Commit happens automatically on successful exit
            # Rollback happens automatically on exception
    
    Requirements: 19.4, 19.5
    """
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize Unit of Work.
        
        Args:
            session: Optional existing session for nested transactions.
                    If None, creates a new session.
        """
        self._session = session
        self._owns_session = session is None
        self._transaction = None
        self._nested = False
    
    async def __aenter__(self) -> "UnitOfWork":
        """
        Enter async context manager.
        
        Creates session and begins transaction.
        Supports nested transactions via SAVEPOINT.
        
        Returns:
            Self with active session and transaction
        """
        # Create new session if not provided
        if self._owns_session:
            self._session = AsyncSessionLocal()
        
        # Check if we're in a nested transaction
        if self._session.in_transaction():
            # Use SAVEPOINT for nested transaction
            self._transaction = await self._session.begin_nested()
            self._nested = True
        else:
            # Begin new transaction
            self._transaction = await self._session.begin()
            self._nested = False
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit async context manager.
        
        Commits transaction on success, rolls back on exception.
        Closes session if we own it.
        
        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        try:
            if exc_type is not None:
                # Exception occurred - rollback
                await self._transaction.rollback()
            else:
                # Success - commit
                await self._transaction.commit()
        except SQLAlchemyError as e:
            # Rollback failed or commit failed
            await self._transaction.rollback()
            raise DatabaseError(
                message="Transaction failed",
                details={"error": str(e)}
            )
        finally:
            # Close session if we own it
            if self._owns_session and self._session:
                await self._session.close()
    
    @property
    def session(self) -> AsyncSession:
        """
        Get the database session.
        
        Returns:
            Active database session
        """
        if self._session is None:
            raise RuntimeError("UnitOfWork not initialized. Use 'async with' context manager.")
        return self._session
    
    async def commit(self) -> None:
        """
        Explicitly commit the transaction.
        
        Note: Usually not needed as commit happens automatically on context exit.
        Use this for explicit commit points within a transaction.
        """
        if self._transaction:
            await self._transaction.commit()
    
    async def rollback(self) -> None:
        """
        Explicitly rollback the transaction.
        
        Note: Usually not needed as rollback happens automatically on exception.
        Use this for explicit rollback points within a transaction.
        """
        if self._transaction:
            await self._transaction.rollback()
    
    async def flush(self) -> None:
        """
        Flush pending changes to database without committing.
        
        Useful for:
        - Getting auto-generated IDs before commit
        - Validating constraints before commit
        - Intermediate state synchronization
        """
        if self._session:
            await self._session.flush()


@asynccontextmanager
async def transactional_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for transactional database sessions.
    
    Provides automatic transaction management:
    - Begins transaction on entry
    - Commits on successful exit
    - Rolls back on exception
    
    This is the recommended way to get a transactional session for
    FastAPI dependency injection.
    
    Usage:
        async def my_endpoint(db: AsyncSession = Depends(transactional_session)):
            # All operations in this function are transactional
            user = User(...)
            db.add(user)
            # Commit happens automatically
    
    Yields:
        AsyncSession: Database session with active transaction
        
    Requirements: 19.4, 19.5
    """
    async with UnitOfWork() as uow:
        try:
            yield uow.session
        except Exception:
            # Exception will be handled by UnitOfWork.__aexit__
            raise


async def get_transactional_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for transactional database sessions.
    
    This is a convenience wrapper around transactional_session()
    for use with FastAPI's Depends().
    
    Usage:
        @app.post("/users")
        async def create_user(
            data: UserCreate,
            db: AsyncSession = Depends(get_transactional_session)
        ):
            user = User(**data.dict())
            db.add(user)
            return user
    
    Yields:
        AsyncSession: Database session with active transaction
    """
    async with transactional_session() as session:
        yield session
