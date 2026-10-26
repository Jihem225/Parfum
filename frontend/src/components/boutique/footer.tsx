import Link from "next/link";
import { Suspense } from "react";
import { getPublic } from "@/lib/server-api";
import type { ShopInfo } from "@/lib/types";

const LINKS = [
  ["/infos/livraison", "Livraison"],
  ["/infos/retours", "Retours"],
  ["/infos/faq", "FAQ"],
  ["/contact", "Contact"],
  ["/suivi", "Suivre ma commande"],
  ["/infos/cgv", "CGV"],
  ["/infos/confidentialite", "Confidentialité"],
  ["/infos/mentions-legales", "Mentions légales"],
] as const;

async function ShopContact() {
  const shop = await getPublic<ShopInfo>("/shop").catch(() => null);
  if (!shop?.whatsapp) return null;
  return (
    <a
      href={`https://wa.me/225${shop.whatsapp}`}
      className="flex h-12 items-center justify-center border border-[#5a514a] text-sm font-semibold text-porcelaine"
    >
      Nous écrire sur WhatsApp
    </a>
  );
}

export function Footer() {
  return (
    <footer className="mt-auto bg-encre px-5 pb-7 pt-9 text-[#e9e4dc]">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <div className="font-display text-lg tracking-[0.24em] text-porcelaine">PROJET PARFUMS</div>
        <nav className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4" aria-label="Informations">
          {LINKS.map(([href, label]) => (
            <Link key={href} href={href} className="text-[#e9e4dc]">
              {label}
            </Link>
          ))}
        </nav>
        <Suspense>
          <ShopContact />
        </Suspense>
        <div className="text-xs text-[#b5ada3]">Projet Parfums · Abidjan, Côte d&apos;Ivoire</div>
      </div>
    </footer>
  );
}
