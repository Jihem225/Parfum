from typing import Any

from sqlalchemy.orm import Session

from app.core.models import AuditLog


def audit(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """Trace une action sensible dans la même transaction que l'action elle-même (RG-53)."""
    db.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            before=before,
            after=after,
            ip=ip,
        )
    )
