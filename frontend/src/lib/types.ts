// Formes des réponses de l'API FastAPI (miroir des schémas Pydantic du backend).

export type Gender = "FEMME" | "HOMME" | "MIXTE";
export type StockStatus = "IN_STOCK" | "LOW" | "OUT";
export type Role = "CUSTOMER" | "COURIER" | "MANAGER" | "OWNER";
export type ProductStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";
export type OrderStatus =
  | "EN_ATTENTE_PAIEMENT"
  | "EN_ATTENTE_CONFIRMATION"
  | "CONFIRMEE"
  | "EN_PREPARATION"
  | "EN_LIVRAISON"
  | "LIVREE"
  | "ECHEC_LIVRAISON"
  | "RETOURNEE"
  | "ANNULEE";
export type PaymentStatus = "A_ENCAISSER" | "A_PAYER" | "PAYE" | "ENCAISSE" | "REMIS" | "ANNULE" | "REMBOURSE";
export type PaymentMethod = "CASH_ON_DELIVERY" | "MOBILE_MONEY";
export type CallResult = "CONFIRMEE" | "PAS_DE_REPONSE" | "ANNULATION_DEMANDEE";
export type FailureReason = "INJOIGNABLE" | "REFUS" | "ADRESSE_INTROUVABLE" | "REPORTEE";
export type MovementType =
  | "ENTREE"
  | "AJUSTEMENT"
  | "RESERVATION"
  | "LIBERATION"
  | "SORTIE_VENTE"
  | "RETOUR"
  | "PERTE";

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type User = {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: Role;
  is_active: boolean;
  totp_enabled: boolean;
  last_login_at: string | null;
};

// --- Catalogue ---
export type Image = { id: number; url: string; alt_text: string; position: number };
export type TaxonRef = { name: string; slug: string };
export type Collection = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  position: number;
  is_active: boolean;
  product_count: number;
};
export type Family = { id: number; name: string; slug: string; position: number; product_count: number };
export type ProductCard = {
  id: number;
  name: string;
  slug: string;
  gender: Gender;
  collection: TaxonRef;
  family: TaxonRef;
  min_price: number;
  volumes: number[];
  stock_status: StockStatus;
  low_stock_count: number | null;
  image: Image | null;
};
export type PublicVariant = {
  id: number;
  volume_ml: number;
  sku: string;
  price: number;
  stock_status: StockStatus;
  low_stock_count: number | null;
};
export type ProductDetail = Omit<ProductCard, "min_price" | "volumes" | "stock_status" | "low_stock_count" | "image"> & {
  description: string;
  top_notes: string;
  heart_notes: string;
  base_notes: string;
  variants: PublicVariant[];
  images: Image[];
  similar: ProductCard[];
};
export type AdminVariant = {
  id: number;
  volume_ml: number;
  sku: string;
  price: number;
  cost_price: number | null;
  stock_physical: number;
  stock_reserved: number;
  available: number;
  low_stock_threshold: number;
  is_active: boolean;
};
export type AdminProduct = {
  id: number;
  name: string;
  slug: string;
  collection_id: number;
  family_id: number;
  gender: Gender;
  description: string;
  top_notes: string;
  heart_notes: string;
  base_notes: string;
  status: ProductStatus;
  published_at: string | null;
  variants: AdminVariant[];
  images: Image[];
};
export type AdminProductRow = {
  id: number;
  name: string;
  slug: string;
  collection: TaxonRef;
  status: ProductStatus;
  volumes: number[];
  min_price: number | null;
  max_price: number | null;
  available: number;
  image: Image | null;
};

// --- Panier et commande ---
export type CartLine = {
  variant_id: number;
  product_name: string;
  product_slug: string;
  volume_ml: number;
  sku: string;
  unit_price: number;
  quantity: number;
  line_total: number;
  max_quantity: number;
  image: Image | null;
  issue: "UNAVAILABLE" | "INSUFFICIENT_STOCK" | null;
};
export type Cart = {
  items: CartLine[];
  item_count: number;
  subtotal: number;
  exceeds_cod_limit: boolean;
  mobile_money: boolean; // paiement en ligne disponible (sans plafond)
  can_checkout: boolean;
};
export type Commune = {
  id: number;
  name: string;
  delivery_fee: number;
  delay_label: string;
  is_active: boolean;
  position: number;
};
export type CheckoutPreview = {
  cart: Cart;
  commune_name: string;
  delivery_fee: number;
  delivery_delay_label: string;
  discount: number;
  promo_code: string | null;
  promo_error: string | null; // code saisi refusé : total sans réduction
  total: number;
  exceeds_cod_limit: boolean;
  can_order: boolean;
};
export type OrderLine = {
  variant_id: number;
  product_name: string;
  volume_ml: number;
  sku: string;
  unit_price: number;
  quantity: number;
  line_total: number;
};
export type Order = {
  number: string;
  status: OrderStatus;
  created_at: string;
  customer_name: string;
  phone: string;
  email: string | null;
  commune_name: string;
  address_line: string;
  landmark: string | null;
  delivery_fee: number;
  delivery_delay_label: string;
  subtotal: number;
  discount: number;
  promo_code: string | null;
  total: number;
  payment_method: PaymentMethod;
  items: OrderLine[];
  history: { status: OrderStatus; at: string }[];
  can_cancel: boolean;
  payment_token: string | null; // mobile money non payé : permet d'ouvrir le paiement
};
export type PaymentState = { order_status: OrderStatus; payment_status: PaymentStatus };
export type OrderSummary = {
  number: string;
  status: OrderStatus;
  created_at: string;
  total: number;
  item_count: number;
};
export type Person = { id: number; full_name: string };
export type OrderEvent = {
  kind: "STATUS_CHANGE" | "CALL" | "DELIVERY_ATTEMPT" | "NOTE";
  from_status: OrderStatus | null;
  to_status: OrderStatus | null;
  call_result: CallResult | null;
  failure_reason: FailureReason | null;
  note: string | null;
  author: string | null;
  at: string;
};
export type AdminOrder = Order & {
  id: number;
  user_id: number | null;
  payment_status: PaymentStatus;
  courier: Person | null;
  delivery_attempts: number;
  cancel_reason: string | null;
  events: OrderEvent[];
  unanswered_calls: number;
  should_cancel: boolean;
};
export type AdminOrderRow = {
  number: string;
  status: OrderStatus;
  created_at: string;
  customer_name: string;
  phone: string;
  commune_name: string;
  total: number;
  payment_status: PaymentStatus;
  courier_name: string | null;
};

// --- Compte client ---
export type Address = {
  id: number;
  label: string | null;
  recipient_name: string;
  phone: string;
  commune_id: number;
  commune_name: string;
  commune_served: boolean;
  address_line: string;
  landmark: string | null;
  is_default: boolean;
};

// --- Back-office ---
export type StockRow = {
  variant_id: number;
  product_id: number;
  product_name: string;
  volume_ml: number;
  sku: string;
  is_active: boolean;
  stock_physical: number;
  stock_reserved: number;
  available: number;
  low_stock_threshold: number;
  is_low: boolean;
};
export type Movement = {
  id: number;
  created_at: string;
  variant_id: number;
  product_name: string;
  volume_ml: number;
  sku: string;
  type: MovementType;
  delta_physical: number;
  delta_reserved: number;
  reason: string | null;
  order_number: string | null;
  author: string | null;
};
export type Delivery = {
  number: string;
  status: OrderStatus;
  customer_name: string;
  phone: string;
  commune_name: string;
  address_line: string;
  landmark: string | null;
  amount_to_collect: number;
  delivery_attempts: number;
  items: { product_name: string; volume_ml: number; quantity: number }[];
};
export type PendingCash = {
  courier: Person;
  amount: number;
  orders: { number: string; amount: number; collected_at: string | null }[];
};
export type Remittance = {
  id: number;
  created_at: string;
  courier: Person;
  received_by: Person;
  expected_amount: number;
  received_amount: number;
  difference: number;
  note: string | null;
  order_numbers: string[];
};
export type Dashboard = {
  date_from: string;
  date_to: string;
  revenue: number;
  discounts: number;
  delivery_fees: number;
  delivered_orders: number;
  average_basket: number | null;
  orders_created: number;
  orders_by_status: Partial<Record<OrderStatus, number>>;
  delivery_success_rate: number | null;
  best_sellers: { product_name: string; volume_ml: number; quantity: number; revenue: number }[];
  to_process: Partial<Record<OrderStatus, number>>;
  low_stock_variants: number;
  cash_held_by_couriers: number;
  new_contact_messages: number;
  failed_emails: number;
};
export type Customer = {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  is_active: boolean;
  created_at: string;
  orders_count: number;
  delivered_total: number;
};
export type ContactMessage = {
  id: number;
  created_at: string;
  name: string;
  phone: string | null;
  email: string | null;
  message: string;
  status: "NOUVEAU" | "TRAITE";
};
export type PromoKind = "PERCENT" | "FIXED";
export type PromoCode = {
  id: number;
  code: string;
  kind: PromoKind;
  value: number;
  max_discount: number | null;
  min_subtotal: number | null;
  starts_at: string | null;
  ends_at: string | null;
  max_uses: number | null;
  is_active: boolean;
  note: string;
  created_at: string;
  uses: number;
  discount_total: number;
};
export type EmailStatus = "PENDING" | "SENT" | "FAILED";
export type OutboxEmail = {
  id: number;
  created_at: string;
  to_address: string;
  subject: string;
  status: EmailStatus;
  attempts: number;
  next_attempt_at: string;
  last_error: string | null;
  sent_at: string | null;
};
export type ShopInfo = {
  name: string;
  phone: string | null;
  whatsapp: string | null;
  email: string | null;
  address: string;
  opening_hours: string;
};
export type AuditEntry = {
  id: number;
  created_at: string;
  author: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ip: string | null;
};
