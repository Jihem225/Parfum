import type { Metadata } from "next";
import { Suspense } from "react";
import { PaymentStatus } from "./payment-status";

export const metadata: Metadata = { title: "Paiement de la commande", robots: { index: false } };

/** Retour du prestataire de mobile money (et page de nouvel essai après un échec). */
export default function PaiementPage({ searchParams }: PageProps<"/commande/paiement">) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 px-4 py-10 text-center">
      <Suspense>
        {searchParams.then((p) => (
          <PaymentStatus number={typeof p.numero === "string" ? p.numero : ""} token={typeof p.t === "string" ? p.t : ""} />
        ))}
      </Suspense>
    </div>
  );
}
