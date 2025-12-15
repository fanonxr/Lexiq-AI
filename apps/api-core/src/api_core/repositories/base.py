"""Base repository class with common CRUD operations."""

import logging
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Base
from api_core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# Type variable for the model type
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        try:
            result = await self.session.execute(select(self.model).where(self.model.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} by ID {id}: {e}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__}") from e

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[dict] = None
    ) -> List[ModelType]:
        """
        Get all records with optional pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional dictionary of filters (field: value)

        Returns:
            List of model instances
        """
        try:
            query = select(self.model)

            # Apply filters if provided
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.where(getattr(self.model, field) == value)

            query = query.offset(skip).limit(limit)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__} records") from e

    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            await self.session.flush()  # Flush to get the ID
            await self.session.refresh(instance)
            logger.debug(f"Created {self.model.__name__} with ID: {instance.id}")
            return instance
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            await self.session.rollback()
            raise DatabaseError(f"Failed to create {self.model.__name__}") from e

    async def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """
        Update a record by ID.

        Args:
            id: Record ID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found
        """
        try:
            # Get the instance first
            instance = await self.get_by_id(id)
            if not instance:
                return None

            # Update fields
            for field, value in kwargs.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)

            await self.session.flush()
            await self.session.refresh(instance)
            logger.debug(f"Updated {self.model.__name__} with ID: {id}")
            return instance
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model.__name__} with ID {id}: {e}")
            await self.session.rollback()
            raise DatabaseError(f"Failed to update {self.model.__name__}") from e

    async def delete(self, id: str) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        try:
            instance = await self.get_by_id(id)
            if not instance:
                return False

            await self.session.delete(instance)
            await self.session.flush()
            logger.debug(f"Deleted {self.model.__name__} with ID: {id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model.__name__} with ID {id}: {e}")
            await self.session.rollback()
            raise DatabaseError(f"Failed to delete {self.model.__name__}") from e

    async def count(self, filters: Optional[dict] = None) -> int:
        """
        Count records with optional filtering.

        Args:
            filters: Optional dictionary of filters

        Returns:
            Number of records
        """
        try:
            from sqlalchemy import func

            query = select(func.count()).select_from(self.model)

            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.where(getattr(self.model, field) == value)

            result = await self.session.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to count {self.model.__name__} records") from e

    async def exists(self, id: str) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Record ID

        Returns:
            True if exists, False otherwise
        """
        instance = await self.get_by_id(id)
        return instance is not None
