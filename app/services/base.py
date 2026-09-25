"""Base service class for HealthSetu business logic layer."""

from typing import Generic, TypeVar

RepositoryType = TypeVar("RepositoryType")


class BaseService(Generic[RepositoryType]):
    """Base class for domain service implementations.

    Business logic resides exclusively in the service layer, coordinating between
    repositories and external integration adapters.
    """

    def __init__(self, repository: RepositoryType | None = None) -> None:
        self._repository = repository

    @property
    def repository(self) -> RepositoryType | None:
        return self._repository
