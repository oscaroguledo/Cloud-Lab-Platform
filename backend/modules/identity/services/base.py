"""Base service class with common CRUD operations."""

import uuid
from typing import Generic, TypeVar, Optional, Type

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_structured_logger

logger = get_structured_logger(__name__)

T = TypeVar("T")  # Model type


class BaseService(Generic[T]):
    """Base service with common database operations."""

    def __init__(self, model: Type[T]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[T]:
        """Fetch a single record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def list(
        self, db: AsyncSession, limit: int = 50, offset: int = 0, **filters
    ) -> tuple[list[T], int]:
        """Fetch paginated records with optional filters."""
        query = select(self.model)

        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.where(getattr(self.model, key) == value)

        # Get total count
        count_query = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                count_query = count_query.where(getattr(self.model, key) == value)
        total = await db.scalar(count_query)

        # Apply pagination
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        items = result.scalars().all()

        return items, total

    async def create(self, db: AsyncSession, **data) -> T:
        """Create a new record."""
        instance = self.model(**data)
        db.add(instance)
        await db.flush()
        return instance

    async def update(self, db: AsyncSession, instance: T, **data) -> T:
        """Update an existing record."""
        for key, value in data.items():
            if value is not None and hasattr(instance, key):
                setattr(instance, key, value)
        await db.flush()
        return instance

    async def delete(self, db: AsyncSession, instance: T) -> None:
        """Delete a record."""
        await db.delete(instance)
        await db.flush()

    async def exists(self, db: AsyncSession, **filters) -> bool:
        """Check if a record exists matching the filters."""
        query = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.where(getattr(self.model, key) == value)
        count = await db.scalar(query)
        return count > 0
