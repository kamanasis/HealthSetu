"""Base repository layer defining database access boundary.

NOTE:
Database models and tables are owned by the Database Team.
This base repository provides standard session interaction without binding to unagreed schemas.
"""

from typing import Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Generic repository pattern interface for SQLAlchemy data access."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
