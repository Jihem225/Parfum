import type { Metadata } from "next";
import { Suspense } from "react";
import { SimulatedCheckout } from "./simulated-checkout";

export const metadata: Metadata = { title: "Paiement simulé", robots: { index: false } };

/** Fausse page de prestataire (développement et CI) : le backend la refuse en production. */
export default function SimulationPage({ searchParams }: PageProps<"/paiement/simulation">) {
  return (
    <div className="flex flex-1 items-start justify-center bg-[#1f2a37] px-4 py-10">
      <Suspense>
        {searchParams.then((p) => (
          <SimulatedCheckout
            number={typeof p.numero === "string" ? p.numero : ""}
            amount={Number(p.montant) || 0}
            back={typeof p.retour === "string" ? p.retour : ""}
          />
        ))}
      </Suspense>
    </div>
  );
}
