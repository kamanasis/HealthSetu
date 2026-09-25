"""Permission data access repository — database team contract definition.

DATABASE TEAM DEPENDENCY — PHASE 3
====================================
This repository defines the data access contract for:

1. Role-Permission mapping table
   Required fields:
     id          : Primary Key
     role        : VARCHAR / ENUM matching UserRole values
     permission  : VARCHAR matching Permission values
     is_active   : BOOLEAN DEFAULT TRUE
     created_at  : TIMESTAMP WITH TIME ZONE

2. Optional: Per-user permission overrides
   (Not implemented in Phase 3 — static role→permission map used)

Until the database team delivers these, this repository falls back to
the static policy defined in app/core/policies.py.
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.core.policies import Permission, get_role_permissions


class PermissionRepository(BaseRepository[Any]):
    """Repository for role/permission data access.

    Current implementation uses the static ROLE_PERMISSIONS map from
    app/core/policies.py as the authoritative source.

    When the Database Team delivers a dynamic role-permission table:
    - Replace get_permissions_for_role() with a database query.
    - The rest of the authorization service remains unchanged.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)  # type: ignore[arg-type]

    async def get_permissions_for_role(self, role: str) -> frozenset[Permission]:
        """Return the set of permissions for the given role.

        Deny by default: unknown roles receive an empty frozenset.

        NOTE FOR DATABASE TEAM:
        When dynamic permission tables are ready, replace with:
            stmt = select(RolePermissionModel).where(
                RolePermissionModel.role == role,
                RolePermissionModel.is_active == True,
            )
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            return frozenset(Permission(row.permission) for row in rows)
        """
        return get_role_permissions(role)

    async def role_has_permission(self, role: str, permission: Permission) -> bool:
        """Check whether the given role includes the specified permission."""
        perms = await self.get_permissions_for_role(role)
        return permission in perms
