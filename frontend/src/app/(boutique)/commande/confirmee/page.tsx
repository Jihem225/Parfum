import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { buttonClass } from "@/components/ui";

export const metadata: Metadata = { title: "Commande enregistrée", robots: { index: false } };

async function Confirmation({ searchParams }: Pick<PageProps<"/commande/confirmee">, "searchParams">) {
  const numero = (await searchParams).numero;
  const number = typeof numero === "string" ? numero : "";
  return (
    <>
      <p className="text-encre-douce">Votre numéro de commande</p>
      <p className="text-3xl font-bold tracking-[0.04em]">{number}</p>
      <ol className="flex list-decimal flex-col gap-2 pl-5 text-left text-[15px]">
        <li>Nous vous appelons pour confirmer la commande.</li>
        <li>Votre colis est préparé puis confié à un livreur.</li>
        <li>Vous payez en espèces à la réception.</li>
      </ol>
      <Link href={`/suivi?numero=${encodeURIComponent(number)}`} className={buttonClass()}>
        Suivre ma commande
      </Link>
    </>
  );
}

export default function ConfirmeePage({ searchParams }: PageProps<"/commande/confirmee">) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 px-4 py-10 text-center">
      <h1 className="font-display text-[32px]">Merci, c&apos;est enregistré</h1>
      <Suspense>
        <Confirmation searchParams={searchParams} />
      </Suspense>
      <Link href="/parfums" className="text-sm font-semibold underline underline-offset-4">Continuer mes achats</Link>
    </div>
  );
}
