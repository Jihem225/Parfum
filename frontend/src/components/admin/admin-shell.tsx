"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { ROLE } from "@/lib/format";
import { homeFor } from "@/lib/navigation";
import { useMe } from "@/lib/hooks";
import { TotpSetup } from "./totp-setup";

const NAV: [string, string, boolean][] = [
  // chemin, libellé, réservé au Propriétaire
  ["/admin", "Tableau de bord", false],
  ["/admin/commandes", "Commandes", false],
  ["/admin/produits", "Produits", false],
  ["/admin/collections", "Collections et familles", false],
  ["/admin/stock", "Stock", false],
  ["/admin/encaissements", "Encaissements", false],
  ["/admin/clients", "Clients", false],
  ["/admin/messages", "Messages", false],
  ["/admin/emails", "E-mails", false],
  ["/admin/parametres", "Boutique et livraison", true],
  ["/admin/equipe", "Collaborateurs", true],
  ["/admin/journal", "Journal d'audit", true],
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const { data: me, isLoading } = useMe();
  const router = useRouter();
  const pathname = usePathname();
  const qc = useQueryClient();
  const staff = me && (me.role === "MANAGER" || me.role === "OWNER");

  useEffect(() => {
    if (isLoading) return;
    if (!me) router.replace(`/admin/connexion?suite=${encodeURIComponent(pathname)}`);
    else if (!staff) router.replace(homeFor(me.role));
  }, [me, isLoading, staff, pathname, router]);

  if (!me || !staff) return <Loading />;
  const active = (href: string) => (href === "/admin" ? pathname === href : pathname.startsWith(href));
  return (
    <div className="flex min-h-screen flex-col bg-admin md:flex-row">
      <aside className="no-print flex flex-col gap-4 bg-encre p-4 md:w-60 md:flex-none md:py-6">
        <div className="px-2">
          <div className="font-display text-[15px] tracking-[0.22em] text-porcelaine">PROJET PARFUMS</div>
          <div className="mt-1 text-xs text-[#a39b91]">Administration</div>
        </div>
        {me.totp_enabled && (
          <nav className="flex gap-1 overflow-x-auto md:flex-col" aria-label="Administration">
            {NAV.filter(([, , ownerOnly]) => !ownerOnly || me.role === "OWNER").map(([href, label]) => (
              <Link
                key={href}
                href={href}
                aria-current={active(href) ? "page" : undefined}
                className="whitespace-nowrap rounded px-3 py-2 text-sm text-[#d9d3ca] hover:text-porcelaine aria-[current=page]:bg-porcelaine aria-[current=page]:font-bold aria-[current=page]:text-encre"
              >
                {label}
              </Link>
            ))}
          </nav>
        )}
        <div className="mt-auto flex items-center justify-between gap-2 border-t border-[#3a322c] px-2 pt-3 text-sm text-[#d9d3ca]">
          <span>
            {me.full_name}
            <br />
            <span className="text-[#a39b91]">{ROLE[me.role]}</span>
          </span>
          <button
            type="button"
            className="underline underline-offset-4"
            onClick={async () => {
              await api("/auth/logout", { method: "POST" });
              qc.clear();
              router.push("/admin/connexion");
            }}
          >
            Quitter
          </button>
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col gap-5 p-4 md:p-8">{me.totp_enabled ? children : <TotpSetup />}</main>
    </div>
  );
}
