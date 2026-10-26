const fcfa = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

/** Formate un montant entier en FCFA : 61500 → « 61 500 FCFA ». */
export function formatFCFA(amount: number): string {
  if (!Number.isSafeInteger(amount)) {
    throw new Error(`Montant FCFA non entier : ${amount}`);
  }
  return `${fcfa.format(amount)} FCFA`;
}
