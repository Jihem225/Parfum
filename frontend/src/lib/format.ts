import type { FailureReason, Gender, MovementType, OrderStatus, PaymentStatus, ProductStatus, Role } from "./types";

const fcfa = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

/** Formate un montant entier en FCFA : 61500 → « 61 500 FCFA ». */
export function formatFCFA(amount: number): string {
  if (!Number.isSafeInteger(amount)) {
    throw new Error(`Montant FCFA non entier : ${amount}`);
  }
  return `${fcfa.format(amount)}\u00a0FCFA`; // insécable : la devise ne passe pas seule à la ligne
}

const dateTime = new Intl.DateTimeFormat("fr-FR", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Africa/Abidjan",
});
const dateOnly = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeZone: "Africa/Abidjan" });

export const formatDateTime = (iso: string) => dateTime.format(new Date(iso));
export const formatDate = (iso: string) => dateOnly.format(new Date(iso));

/** « 0708123456 » → « 07 08 12 34 56 ». */
export function formatPhone(phone: string): string {
  return phone.replace(/(\d{2})(?=\d)/g, "$1 ");
}

export const ORDER_STATUS: Record<OrderStatus, string> = {
  EN_ATTENTE_CONFIRMATION: "En attente de confirmation",
  CONFIRMEE: "Confirmée",
  EN_PREPARATION: "En préparation",
  EN_LIVRAISON: "En livraison",
  LIVREE: "Livrée",
  ECHEC_LIVRAISON: "Échec de livraison",
  RETOURNEE: "Retournée",
  ANNULEE: "Annulée",
};

export const PAYMENT_STATUS: Record<PaymentStatus, string> = {
  A_ENCAISSER: "À encaisser",
  ENCAISSE: "Encaissé",
  REMIS: "Remis en caisse",
  ANNULE: "Annulé",
  REMBOURSE: "Remboursé",
};

export const PRODUCT_STATUS: Record<ProductStatus, string> = { DRAFT: "Brouillon", PUBLISHED: "Publié", ARCHIVED: "Archivé" };

export const GENDER: Record<Gender, string> = { FEMME: "Femme", HOMME: "Homme", MIXTE: "Mixte" };

export const ROLE: Record<Role, string> = {
  CUSTOMER: "Client",
  COURIER: "Livreur",
  MANAGER: "Gestionnaire",
  OWNER: "Propriétaire",
};

export const FAILURE_REASON: Record<FailureReason, string> = {
  INJOIGNABLE: "Client injoignable",
  REFUS: "Refus du client",
  ADRESSE_INTROUVABLE: "Adresse introuvable",
  REPORTEE: "Livraison reportée",
};

export const MOVEMENT: Record<MovementType, string> = {
  ENTREE: "Entrée",
  AJUSTEMENT: "Ajustement",
  RESERVATION: "Réservation",
  LIBERATION: "Libération",
  SORTIE_VENTE: "Sortie (vente)",
  RETOUR: "Retour",
  PERTE: "Perte",
};

/** Libellé de disponibilité (RG-16). */
export function stockLabel(status: "IN_STOCK" | "LOW" | "OUT", count: number | null): string {
  if (status === "OUT") return "Rupture de stock";
  if (status === "LOW") return `Plus que ${count ?? "quelques"} en stock`;
  return "En stock";
}

// Fond teinté par parfum : la charte prévoit la couleur du jus ; en attendant, une palette chaude.
const TINTS = ["#EBDCC4", "#DED2C7", "#EEE6CB", "#E3D1B4", "#D9E0D3", "#E8D5CF"];
export const tint = (id: number): string => TINTS[id % TINTS.length] ?? "#EBDCC4";
