"""E-mails de commande (§3.5) : au client s'il a donné un e-mail, à la boutique pour les
nouvelles commandes. Envoyés après validation de la transaction."""

from app.core.config import settings
from app.modules.orders.models import Order, OrderItem, OrderStatus

Message = tuple[str, str, str]  # destinataire, objet, texte


def fcfa(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " FCFA"


def _track_link(order: Order) -> str:
    return f"{settings.frontend_origin}/suivi?numero={order.number}"


def to_customer(order: Order, *, prepaid: bool = False) -> Message | None:
    if not order.email:
        return None
    n, total = order.number, fcfa(order.total)
    texts = {
        OrderStatus.EN_ATTENTE_CONFIRMATION: (
            f"Commande {n} reçue",
            f"Nous avons bien reçu votre commande {n}. Nous allons vous appeler au "
            f"{order.phone} pour la confirmer.\n\nMontant à payer en espèces à la livraison : "
            f"{total}.",
        ),
        OrderStatus.CONFIRMEE: (
            f"Commande {n} confirmée",
            f"Votre commande {n} est confirmée. Livraison à {order.commune_name}, délai indicatif "
            f"{order.delivery_delay_label}.",
        ),
        OrderStatus.EN_LIVRAISON: (
            f"Commande {n} en route",
            f"Votre commande {n} est partie en livraison. "
            + ("Elle est déjà payée." if prepaid else f"Merci de prévoir {total} en espèces."),
        ),
        OrderStatus.LIVREE: (
            f"Commande {n} livrée",
            f"Votre commande {n} vous a été remise. Merci pour votre confiance.",
        ),
        OrderStatus.ANNULEE: (
            f"Commande {n} annulée",
            f"Votre commande {n} a été annulée. Pour toute question, répondez à ce message.",
        ),
    }
    if order.status not in texts:
        return None
    subject, body = texts[order.status]
    return (
        order.email,
        subject,
        f"Bonjour {order.customer_name},\n\n{body}\n\nSuivre votre commande : {_track_link(order)}",
    )


def to_shop(order: Order, items: list[OrderItem], *, prepaid: bool = False) -> Message | None:
    if not settings.shop_notification_email:
        return None
    lines = "\n".join(
        f"- {i.quantity} × {i.product_name} {i.volume_ml} ml ({i.sku}) : {fcfa(i.line_total)}"
        for i in items
    )
    return (
        settings.shop_notification_email,
        f"Nouvelle commande {order.number} — {fcfa(order.total)}",
        f"{order.customer_name} — {order.phone}\n{order.commune_name}, {order.address_line}\n\n"
        f"{lines}\nLivraison : {fcfa(order.delivery_fee)}\n"
        + (
            f"Payée par mobile money : {fcfa(order.total)}. Déjà confirmée, à préparer."
            if prepaid
            else f"Total à encaisser : {fcfa(order.total)}\n\nÀ confirmer par téléphone."
        ),
    )


def late_payment(order: Order) -> Message | None:
    if not settings.shop_notification_email:
        return None
    return (
        settings.shop_notification_email,
        f"À rembourser : paiement reçu sur la commande annulée {order.number}",
        f"Le paiement mobile money de {fcfa(order.total)} est arrivé après l'annulation de la "
        f"commande {order.number} ({order.customer_name}, {order.phone}). Remboursez-le depuis le "
        "tableau de bord du prestataire, puis enregistrez le remboursement dans le back-office.",
    )
