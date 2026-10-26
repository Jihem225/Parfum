"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { PayButton } from "@/components/pay-button";
import { Alert, buttonClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import type { PaymentState } from "@/lib/types";

export function PaymentStatus({ number, token }: { number: string; token: string }) {
  const router = useRouter();
  const state = useQuery({
    queryKey: ["payment", number],
    queryFn: () => api<PaymentState>(`/orders/${encodeURIComponent(number)}/payment?token=${encodeURIComponent(token)}`),
    enabled: !!number && !!token,
    // L'avis du prestataire peut arriver quelques secondes après le retour du client.
    refetchInterval: (q) => (q.state.data?.order_status === "EN_ATTENTE_PAIEMENT" ? 3000 : false),
  });
  const s = state.data;
  const paid = s?.payment_status === "PAYE" && s.order_status !== "ANNULEE";
  useEffect(() => {
    if (paid) router.replace(`/commande/confirmee?numero=${encodeURIComponent(number)}&paye=1`);
  }, [paid, number, router]);

  if (!number || !token || state.isError) {
    return (
      <>
        <h1 className="font-display text-[32px]">Paiement</h1>
        <Alert>{state.isError ? errorMessage(state.error) : "Lien de paiement incomplet."}</Alert>
        <Link href="/suivi" className={buttonClass("secondary")}>Suivre une commande</Link>
      </>
    );
  }
  if (!s || paid) return <Loading label="Vérification du paiement…" />;

  if (s.order_status === "EN_ATTENTE_PAIEMENT") {
    return (
      <>
        <h1 className="font-display text-[32px]">Paiement en attente</h1>
        <p className="text-3xl font-bold tracking-[0.04em]">{number}</p>
        <p className="text-[15px]">
          Si vous avez validé le paiement sur votre téléphone, la confirmation arrive dans quelques instants : cette page se met à jour
          toute seule.
        </p>
        <p className="text-sm text-encre-douce">
          Paiement refusé ou abandonné ? Vous pouvez réessayer. Sans paiement dans les 30 minutes suivant la commande, elle est annulée.
        </p>
        <PayButton number={number} token={token} label="Réessayer le paiement" />
      </>
    );
  }

  // Annulée : délai dépassé, ou paiement arrivé après l'annulation (remboursé par la boutique).
  return (
    <>
      <h1 className="font-display text-[32px]">Commande annulée</h1>
      <p className="text-3xl font-bold tracking-[0.04em]">{number}</p>
      {s.payment_status === "PAYE" || s.payment_status === "REMBOURSE" ? (
        <Alert tone="info">
          Votre paiement est arrivé après l&apos;annulation de la commande. La boutique vous rembourse ;{" "}
          <Link href="/contact" className="font-semibold underline">contactez-nous</Link> pour toute question.
        </Alert>
      ) : (
        <p className="text-[15px]">Aucun paiement n&apos;a été reçu pour cette commande : rien ne vous a été débité.</p>
      )}
      <Link href="/parfums" className={buttonClass()}>Retour aux parfums</Link>
    </>
  );
}
