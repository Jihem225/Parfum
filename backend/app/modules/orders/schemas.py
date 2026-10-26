from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.core.validators import PersonName, Phone
from app.modules.auth.schemas import Email
from app.modules.cart.schemas import CartOut
from app.modules.orders.models import CallResult, EventKind, FailureReason, OrderStatus
from app.modules.payments.models import PaymentMethod, PaymentStatus

AddressLine = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=255)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
PromoInput = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, max_length=30)]
OrderNumber = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=3, max_length=20)
]


class CheckoutIn(BaseModel):
    customer_name: PersonName
    phone: Phone
    email: Email | None = None  # facultatif pour un invité (RG-24)
    commune_id: int
    address_line: AddressLine
    landmark: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""
    accept_terms: bool  # CGV (RG-29)
    expected_total: Annotated[int, Field(gt=0)]  # total affiché au client : un écart est signalé
    idempotency_key: Annotated[str, StringConstraints(min_length=16, max_length=64)]
    payment_method: PaymentMethod = PaymentMethod.CASH_ON_DELIVERY
    promo_code: PromoInput = ""


class PreviewIn(BaseModel):
    commune_id: int
    payment_method: PaymentMethod = PaymentMethod.CASH_ON_DELIVERY
    promo_code: PromoInput = ""
    phone: Annotated[str, StringConstraints(max_length=30)] = ""  # saisie en cours : tolérée


class CheckoutPreview(BaseModel):
    """Récapitulatif calculé par le serveur : son `total` est l'`expected_total` à renvoyer."""

    cart: CartOut
    commune_name: str
    delivery_fee: int
    delivery_delay_label: str
    discount: int  # code promo valable ; 0 sinon
    promo_code: str | None  # code appliqué
    promo_error: str | None  # motif du refus du code saisi (le total est alors sans réduction)
    total: int
    exceeds_cod_limit: bool
    can_order: bool


class TrackIn(BaseModel):
    number: OrderNumber
    phone: Phone


class CancelIn(BaseModel):
    reason: Note = ""


class CallIn(BaseModel):
    result: CallResult
    note: Note = ""


# Transitions du back-office traitées ici ; livraison, échec et retour passent par l'étape 6.9.
StaffTarget = Literal[
    OrderStatus.CONFIRMEE, OrderStatus.EN_PREPARATION, OrderStatus.EN_LIVRAISON, OrderStatus.ANNULEE
]


class TransitionIn(BaseModel):
    to: StaffTarget
    courier_id: int | None = None  # obligatoire pour « En livraison » (RG-41)
    note: Note = ""  # motif, obligatoire pour une annulation


class ReturnLine(BaseModel):
    variant_id: int
    restocked: Annotated[int, Field(ge=0, le=5)]  # en bon état : retour en stock
    lost: Annotated[int, Field(ge=0, le=5)] = 0  # abîmé : perte


class RefundIn(BaseModel):
    amount: Annotated[int, Field(gt=0)]
    note: Note = ""


class PaymentStart(BaseModel):
    token: Annotated[str, StringConstraints(max_length=64)]


class PaymentState(BaseModel):
    order_status: OrderStatus
    payment_status: PaymentStatus


class PaymentLink(BaseModel):
    url: str  # page de paiement hébergée par le prestataire


class SimulatedPayment(BaseModel):
    token: Annotated[str, StringConstraints(max_length=64)]
    paid: bool


class ReturnIn(BaseModel):
    items: Annotated[list[ReturnLine], Field(min_length=1, max_length=20)]
    note: Note = ""
    refund_amount: Annotated[int, Field(ge=0)] | None = None  # commande livrée seulement


class OrderLineOut(BaseModel):
    variant_id: int  # sert aux retours article par article
    product_name: str
    volume_ml: int
    sku: str
    unit_price: int
    quantity: int
    line_total: int


class StatusStep(BaseModel):
    status: OrderStatus
    at: datetime


class OrderOut(BaseModel):
    """Vue client : copie figée de la commande (RG-26) et historique des statuts."""

    number: str
    status: OrderStatus
    created_at: datetime
    customer_name: str
    phone: str
    email: str | None
    commune_name: str
    address_line: str
    landmark: str | None
    delivery_fee: int
    delivery_delay_label: str
    subtotal: int
    discount: int
    promo_code: str | None
    total: int
    payment_method: PaymentMethod
    items: list[OrderLineOut]
    history: list[StatusStep]
    can_cancel: bool
    payment_token: str | None = None  # mobile money non payé : permet d'ouvrir le paiement


class OrderSummary(BaseModel):
    number: str
    status: OrderStatus
    created_at: datetime
    total: int
    item_count: int


class EventOut(BaseModel):
    kind: EventKind
    from_status: OrderStatus | None
    to_status: OrderStatus | None
    call_result: CallResult | None
    failure_reason: FailureReason | None
    note: str | None
    author: str | None
    at: datetime


class PersonRef(BaseModel):
    id: int
    full_name: str


class AdminOrderOut(OrderOut):
    id: int
    user_id: int | None
    payment_status: PaymentStatus
    courier: PersonRef | None
    delivery_attempts: int
    cancel_reason: str | None
    events: list[EventOut]
    unanswered_calls: int
    should_cancel: bool  # RG-31 : 3 appels sans réponse


class AdminOrderRow(BaseModel):
    number: str
    status: OrderStatus
    created_at: datetime
    customer_name: str
    phone: str
    commune_name: str
    total: int
    payment_status: PaymentStatus
    courier_name: str | None


class AdminOrderPage(BaseModel):
    items: list[AdminOrderRow]
    total: int
    page: int
    page_size: int
