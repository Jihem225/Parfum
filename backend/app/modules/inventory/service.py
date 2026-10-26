"""Stock : toute modification passe par `_move`, qui met à jour la contenance ET écrit le
mouvement dans la même transaction (RG-11). La mise à jour est conditionnelle et atomique :
deux commandes simultanées sur la dernière unité ne peuvent pas réussir toutes les deux."""

import logging
from collections.abc import Mapping
from typing import Any

from sqlalchemy import event, select, update
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import settings
from app.core.email import send_email
from app.core.errors import AppError
from app.modules.catalog.models import Product, ProductVariant
from app.modules.inventory.models import MovementType, StockMovement

log = logging.getLogger("parfums.stock")

_ALERTS = "stock_alerts"  # clé de Session.info : alertes à envoyer une fois la transaction validée


def _move(
    db: Session,
    kind: MovementType,
    variant_id: int,
    d_physical: int,
    d_reserved: int,
    *,
    order_id: int | None = None,
    user_id: int | None = None,
    reason: str | None = None,
    active_only: bool = False,
) -> bool:
    """Applique les deltas seulement si le résultat reste cohérent (physique ≥ réservé ≥ 0).
    Renvoie False, sans rien écrire, si la contenance n'existe pas ou si le stock manque."""
    new_physical = ProductVariant.stock_physical + d_physical
    new_reserved = ProductVariant.stock_reserved + d_reserved
    stmt = (
        update(ProductVariant)
        .where(ProductVariant.id == variant_id, new_physical >= new_reserved, new_reserved >= 0)
        .values(stock_physical=new_physical, stock_reserved=new_reserved)
        .returning(
            ProductVariant.stock_physical,
            ProductVariant.stock_reserved,
            ProductVariant.low_stock_threshold,
        )
        .execution_options(synchronize_session="fetch")
    )
    if active_only:
        stmt = stmt.where(ProductVariant.is_active)
    row = db.execute(stmt).one_or_none()
    if row is None:
        return False
    db.add(
        StockMovement(
            variant_id=variant_id,
            type=kind,
            delta_physical=d_physical,
            delta_reserved=d_reserved,
            order_id=order_id,
            user_id=user_id,
            reason=reason,
        )
    )
    after = row.stock_physical - row.stock_reserved
    before = after - d_physical + d_reserved
    if after <= row.low_stock_threshold < before:
        _queue_alert(db, variant_id, after, row.low_stock_threshold)
    return True


def _available(db: Session, variant_ids: list[int]) -> dict[int, int]:
    rows = db.execute(
        select(
            ProductVariant.id, ProductVariant.stock_physical - ProductVariant.stock_reserved
        ).where(ProductVariant.id.in_(variant_ids))
    )
    return {variant_id: available for variant_id, available in rows}


def _apply_lines(
    db: Session,
    kind: MovementType,
    lines: Mapping[int, int],
    physical_sign: int,
    reserved_sign: int,
    *,
    order_id: int | None,
    user_id: int | None,
    error: tuple[str, str],
    active_only: bool = False,
) -> None:
    """Tout ou rien : lignes traitées par identifiant croissant (pas d'interblocage entre deux
    commandes), et la moindre ligne en échec annule toutes les autres (RG-12)."""
    alerts: list[dict[str, Any]] = db.info.setdefault(_ALERTS, [])
    queued = len(alerts)
    with db.begin_nested():
        failed = [
            variant_id
            for variant_id in sorted(lines)
            if not _move(
                db,
                kind,
                variant_id,
                physical_sign * lines[variant_id],
                reserved_sign * lines[variant_id],
                order_id=order_id,
                user_id=user_id,
                active_only=active_only,
            )
        ]
        if failed:
            del alerts[queued:]  # le point de sauvegarde annule aussi les franchissements de seuil
            available = _available(db, failed)
            details = [
                {"variant_id": v, "requested": lines[v], "available": max(available.get(v, 0), 0)}
                for v in failed
            ]
            raise AppError(409, error[0], error[1], details)


def reserve(
    db: Session, lines: Mapping[int, int], *, order_id: int | None, user_id: int | None = None
) -> None:
    """Validation d'une commande (RG-12) : réservé +q si le disponible suffit."""
    _apply_lines(
        db,
        MovementType.RESERVATION,
        lines,
        0,
        1,
        order_id=order_id,
        user_id=user_id,
        error=("INSUFFICIENT_STOCK", "Stock insuffisant pour certains articles."),
        active_only=True,
    )


_INCONSISTENT = ("STOCK_CONFLICT", "Le stock réservé ne correspond pas à la commande.")


def release(
    db: Session, lines: Mapping[int, int], *, order_id: int | None, user_id: int | None = None
) -> None:
    """Annulation avant livraison (RG-14) : réservé −q."""
    _apply_lines(
        db,
        MovementType.LIBERATION,
        lines,
        0,
        -1,
        order_id=order_id,
        user_id=user_id,
        error=_INCONSISTENT,
    )


def ship(
    db: Session, lines: Mapping[int, int], *, order_id: int | None, user_id: int | None
) -> None:
    """Passage « En livraison » (RG-13) : physique −q et réservé −q."""
    _apply_lines(
        db,
        MovementType.SORTIE_VENTE,
        lines,
        -1,
        -1,
        order_id=order_id,
        user_id=user_id,
        error=_INCONSISTENT,
    )


def restock_return(
    db: Session, lines: Mapping[int, int], *, order_id: int | None, user_id: int | None
) -> None:
    """Colis revenu et contrôlé en bon état (RG-15) : physique +q."""
    _apply_lines(
        db,
        MovementType.RETOUR,
        lines,
        1,
        0,
        order_id=order_id,
        user_id=user_id,
        error=_INCONSISTENT,
    )


def record_loss(
    db: Session, variant_id: int, quantity: int, *, order_id: int, user_id: int | None, reason: str
) -> None:
    """Colis revenu abîmé (RG-15) : rien ne revient en stock, le mouvement garde la trace."""
    _move(
        db,
        MovementType.PERTE,
        variant_id,
        0,
        0,
        order_id=order_id,
        user_id=user_id,
        reason=f"{quantity} unité(s) — {reason}",
    )


# --- Back-office ----------------------------------------------------------------------------------


def receive(
    db: Session, variant: ProductVariant, quantity: int, reason: str | None, *, user_id: int
) -> None:
    """Réception de marchandise : physique +q."""
    _move(db, MovementType.ENTREE, variant.id, quantity, 0, user_id=user_id, reason=reason)
    _audit(db, "stock.entry", variant, quantity, reason, user_id)


def adjust(db: Session, variant: ProductVariant, delta: int, reason: str, *, user_id: int) -> None:
    """Correction d'inventaire, motif obligatoire. Refusée si le physique passerait sous le
    réservé : il faut d'abord annuler des commandes."""
    if not _move(db, MovementType.AJUSTEMENT, variant.id, delta, 0, user_id=user_id, reason=reason):
        raise AppError(
            409,
            "BELOW_RESERVED",
            "Ajustement impossible : le stock passerait sous les quantités réservées par des "
            "commandes en cours.",
            {"physical": variant.stock_physical, "reserved": variant.stock_reserved},
        )
    _audit(db, "stock.adjust", variant, delta, reason, user_id)


def _audit(
    db: Session, action: str, variant: ProductVariant, delta: int, reason: str | None, user_id: int
) -> None:
    audit(
        db,
        actor_id=user_id,
        action=action,
        entity_type="variant",
        entity_id=variant.id,
        before={"stock_physical": variant.stock_physical - delta},
        after={"stock_physical": variant.stock_physical, "reason": reason},
    )


# --- Alertes de seuil (RG-17) ---------------------------------------------------------------------


def _queue_alert(db: Session, variant_id: int, available: int, threshold: int) -> None:
    name, volume, sku = db.execute(
        select(Product.name, ProductVariant.volume_ml, ProductVariant.sku)
        .join(Product)
        .where(ProductVariant.id == variant_id)
    ).one()
    alerts: list[dict[str, Any]] = db.info.setdefault(_ALERTS, [])
    alerts.append(
        {"name": name, "volume": volume, "sku": sku, "available": available, "threshold": threshold}
    )


@event.listens_for(Session, "after_commit")
def _send_alerts(session: Session) -> None:
    alerts = session.info.pop(_ALERTS, None)
    if not alerts:
        return
    if not settings.shop_notification_email:
        log.warning(
            "SHOP_NOTIFICATION_EMAIL absente : %d alerte(s) de stock non envoyée(s)", len(alerts)
        )
        return
    lines = [
        f"- {a['name']} {a['volume']} ml ({a['sku']}) : {a['available']} disponible(s), "
        f"seuil {a['threshold']}"
        for a in alerts
    ]
    # shortcut: envoi synchrone après commit (seulement au franchissement d'un seuil) ; passer à
    # une file d'envoi si les e-mails ralentissent les commandes.
    send_email(
        settings.shop_notification_email,
        "Stock bas : " + ", ".join(a["name"] for a in alerts),
        "Ces contenances sont passées au seuil d'alerte ou en dessous :\n\n" + "\n".join(lines),
    )


@event.listens_for(Session, "after_rollback")
def _drop_alerts(session: Session) -> None:
    session.info.pop(_ALERTS, None)
