import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { formatFCFA } from "@/lib/format";
import { getPublic } from "@/lib/server-api";
import type { Commune } from "@/lib/types";

async function CommuneTable() {
  const communes = (await getPublic<Commune[]>("/delivery/communes")) ?? [];
  if (!communes.length) return <p>La liste des communes desservies sera publiée à l&apos;ouverture.</p>;
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-filet"><th className="py-2">Commune</th><th>Frais</th><th>Délai indicatif</th></tr>
      </thead>
      <tbody>
        {communes.map((c) => (
          <tr key={c.id} className="border-b border-filet"><td className="py-2">{c.name}</td><td>{formatFCFA(c.delivery_fee)}</td><td>{c.delay_label}</td></tr>
        ))}
      </tbody>
    </table>
  );
}

// Texte juridique : à fournir par la boutique et à faire valider (aucun texte inventé ici).
const ToProvide = ({ what }: { what: string }) => (
  <p className="border-l-4 border-safran bg-surface p-4">[À compléter : {what}, rédigé par la boutique et validé par un juriste.]</p>
);

const PAGES: Record<string, { title: string; body: ReactNode }> = {
  livraison: {
    title: "Livraison et paiement",
    body: (
      <>
        <p>Nous livrons à Abidjan, dans les communes ci-dessous. Les frais et le délai s&apos;affichent avant de valider votre commande.</p>
        <Suspense fallback={<p>Chargement des communes…</p>}><CommuneTable /></Suspense>
        <p>Après votre commande, nous vous appelons pour la confirmer. Vous payez <strong>en espèces au livreur</strong>, à la réception du colis, le montant exact indiqué.</p>
        <p>Au-delà de 300 000 FCFA par commande, contactez-nous pour organiser la livraison.</p>
      </>
    ),
  },
  retours: {
    title: "Retours",
    body: (
      <>
        <p>Vous pouvez refuser le colis à la livraison : vous ne payez rien.</p>
        <ToProvide what="la politique de retour après livraison (délai, état du produit, remboursement)" />
      </>
    ),
  },
  faq: {
    title: "Questions fréquentes",
    body: (
      <dl className="flex flex-col gap-4">
        {[
          ["Comment payer ?", "En espèces, au livreur, à la réception du colis. Aucun paiement en ligne n'est demandé."],
          ["Faut-il créer un compte ?", "Non. Un compte permet seulement de retrouver vos adresses et vos commandes."],
          ["Combien de flacons puis-je commander ?", "Jusqu'à 5 flacons par contenance et par commande."],
          ["Comment suivre ma commande ?", "Avec votre numéro de commande et votre téléphone, sur la page « Suivre ma commande »."],
          ["Puis-je annuler ?", "Oui, tant que la commande n'est pas partie en livraison : depuis votre compte, ou en nous appelant."],
        ].map(([q, a]) => (
          <div key={q}><dt className="font-semibold">{q}</dt><dd className="text-encre-douce">{a}</dd></div>
        ))}
      </dl>
    ),
  },
  cgv: { title: "Conditions générales de vente", body: <ToProvide what="les conditions générales de vente" /> },
  confidentialite: {
    title: "Confidentialité",
    body: (
      <>
        <p>Nous collectons uniquement les informations nécessaires à votre commande et à sa livraison : nom, téléphone, adresse, e-mail facultatif.</p>
        <ToProvide what="la politique de confidentialité complète (durées de conservation, droits, contact)" />
      </>
    ),
  },
  "mentions-legales": { title: "Mentions légales", body: <ToProvide what="les mentions légales (éditeur, immatriculation, hébergeur)" /> },
};

export function generateStaticParams() {
  return Object.keys(PAGES).map((page) => ({ page }));
}

export async function generateMetadata({ params }: PageProps<"/infos/[page]">): Promise<Metadata> {
  return { title: PAGES[(await params).page]?.title ?? "Information" };
}

export default async function InfoPage({ params }: PageProps<"/infos/[page]">) {
  const page = PAGES[(await params).page];
  if (!page) notFound();
  return (
    <article className="mx-auto flex w-full max-w-2xl flex-col gap-4 px-4 py-6 leading-relaxed">
      <h1 className="font-display text-[32px]">{page.title}</h1>
      {page.body}
    </article>
  );
}
