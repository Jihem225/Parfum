"use client";

import { useMutation } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api";
import { Alert, Button } from "./ui";

/** Ouvre la page de paiement du prestataire (premier essai ou nouvel essai après un échec). */
export function startPayment(number: string, token: string): Promise<void> {
  return api<{ url: string }>(`/orders/${encodeURIComponent(number)}/payment`, { json: { token } }).then(({ url }) => {
    window.location.assign(url);
  });
}

export function PayButton({ number, token, label = "Payer par mobile money" }: { number: string; token: string; label?: string }) {
  const pay = useMutation({ mutationFn: () => startPayment(number, token) });
  // Après le succès, la page change : le bouton reste désactivé pendant la redirection.
  const busy = pay.isPending || pay.isSuccess;
  return (
    <div className="flex flex-col gap-3">
      {pay.isError && <Alert>{errorMessage(pay.error)}</Alert>}
      <Button disabled={busy} onClick={() => pay.mutate()}>
        {busy ? "Ouverture du paiement…" : label}
      </Button>
    </div>
  );
}
