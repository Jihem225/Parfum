"""Journal d'audit (F-49) : lecture seule, Propriétaire uniquement."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.models import AuditLog
from app.modules.auth.deps import DB, Owner
from app.modules.auth.models import User

admin = APIRouter(prefix="/admin/audit-logs", tags=["admin: journal"])


class AuditOut(BaseModel):
    id: int
    created_at: datetime
    author: str | None
    action: str
    entity_type: str
    entity_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    ip: str | None


class AuditPage(BaseModel):
    items: list[AuditOut]
    total: int
    page: int
    page_size: int


@admin.get("")
def audit_logs(
    _: Owner,
    db: DB,
    action: Annotated[str | None, Query(max_length=80)] = None,
    entity_type: Annotated[str | None, Query(max_length=40)] = None,
    entity_id: Annotated[str | None, Query(max_length=40)] = None,
    user_id: int | None = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AuditPage:
    filters = []
    if action:
        filters.append(AuditLog.action.startswith(action, autoescape=True))  # « order » → order.*
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(*filters)
        .order_by(AuditLog.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return AuditPage(
        items=[
            AuditOut(
                id=log.id,
                created_at=log.created_at,
                author=author,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                before=log.before,
                after=log.after,
                ip=log.ip,
            )
            for log, author in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
