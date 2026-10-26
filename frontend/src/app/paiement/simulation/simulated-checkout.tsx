"use client";

import { useMutation } from "@tanstack/react-query";
import { Alert, Button } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatFCFA } from "@/lib/format";
import type { PaymentState } from "@/lib/types";

/** Adresse de retour fournie par le backend : acceptée seulement vers notre page de paiement
 * (pas de redirection ouverte). Le jeton de paiement y figure (`t`). */
function returnUrl(back: string): URL | null {
  try {
    const url = new URL(back, window.location.origin);
    return url.origin === window.location.origin && url.pathname === "/commande/paiement" ? url : null;
  } catch {
    return null;
  }
}

export function SimulatedCheckout({ number, amount, back }: { number: string; amount: number; back: string }) {
  const answer = useMutation({
    mutationFn: (paid: boolean) => {
      const url = returnUrl(back);
      const token = url?.searchParams.get("t");
      if (!url || !token) throw new Error("retour");
      return api<PaymentState>(`/payments/simulation/${encodeURIComponent(number)}`, { json: { token, paid } }).then(() => url);
    },
    onSuccess: (url) => window.location.assign(url),
  });
  const leave = () => {
    const url = returnUrl(back);
    if (url) window.location.assign(url);
  };
  const busy = answer.isPending || answer.isSuccess;

  return (
    <div className="flex w-full max-w-sm flex-col gap-5 rounded-lg bg-white p-6 text-center text-[#1f2a37] shadow-lg">
      <div className="rounded bg-[#fff4d6] px-3 py-2 text-sm font-semibold text-[#7a5300]">Simulation : aucun argent réel n&apos;est débité.</div>
      <div className="flex flex-col gap-1">
        <span className="text-sm text-[#5b6675]">Paiement mobile money</span>
        <span className="text-3xl font-bold">{Number.isSafeInteger(amount) && amount > 0 ? formatFCFA(amount) : "—"}</span>
        <span className="text-sm text-[#5b6675]">Commande {number || "inconnue"}</span>
      </div>
      {answer.isError && <Alert>{answer.error.message === "retour" ? "Lien de paiement invalide." : errorMessage(answer.error)}</Alert>}
      <div className="flex flex-col gap-2">
        <Button disabled={busy || !number} onClick={() => answer.mutate(true)}>
          Confirmer le paiement
        </Button>
        <Button variant="secondary" disabled={busy || !number} onClick={() => answer.mutate(false)}>
          Refuser le paiement
        </Button>
        <Button variant="ghost" disabled={busy} onClick={leave}>
          Revenir à la boutique sans payer
        </Button>
      </div>
    </div>
  );
}
