import type { Metadata } from "next";
import { Suspense } from "react";
import { TrackForm } from "./track-form";

export const metadata: Metadata = { title: "Suivre ma commande" };

export default function SuiviPage({ searchParams }: PageProps<"/suivi">) {
  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-6">
      <h1 className="mb-2 font-display text-[32px]">Suivre ma commande</h1>
      <p className="mb-5 text-sm text-encre-douce">Saisissez le numéro reçu à la commande et votre téléphone.</p>
      <Suspense>
        {searchParams.then((p) => (
          <TrackForm initialNumber={typeof p.numero === "string" ? p.numero : ""} />
        ))}
      </Suspense>
    </div>
  );
}
