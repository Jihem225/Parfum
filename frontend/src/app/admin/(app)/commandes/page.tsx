"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { AdminTitle, Table, td } from "@/components/admin/ui";
import { Alert, inputClass, Loading, StatusPill } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime, formatFCFA, formatPhone, ORDER_STATUS, PAYMENT_STATUS } from "@/lib/format";
import type { AdminOrderRow, OrderStatus, Page } from "@/lib/types";

const TABS: (OrderStatus | "")[] = ["", "EN_ATTENTE_PAIEMENT", "EN_ATTENTE_CONFIRMATION", "CONFIRMEE", "EN_PREPARATION", "EN_LIVRAISON", "ECHEC_LIVRAISON", "LIVREE", "ANNULEE", "RETOURNEE"];

export default function CommandesPage() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const status = (sp.get("statut") ?? "") as OrderStatus | "";
  const q = sp.get("q") ?? "";
  const page = Number(sp.get("page") ?? 1);
  const [search, setSearch] = useState(q);
  const go = (next: Record<string, string>) => {
    const params = new URLSearchParams({ ...(status && { statut: status }), ...(q && { q }), ...next });
    for (const [k, v] of [...params]) if (!v) params.delete(k);
    router.push(`${pathname}?${params}`);
  };
  const query = new URLSearchParams({ page: String(page), ...(status && { status }), ...(q && { q }) });
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-orders", status, q, page],
    queryFn: () => api<Page<AdminOrderRow>>(`/admin/orders?${query}`),
    refetchInterval: 60_000, // nouvelles commandes visibles sans recharger
  });

  return (
    <>
      <AdminTitle
        actions={
          <form onSubmit={(e) => { e.preventDefault(); go({ q: search, page: "" }); }} className="w-full max-w-sm">
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="N° de commande, nom ou téléphone" aria-label="Rechercher une commande" className={`${inputClass} h-10`} />
          </form>
        }
      >
        Commandes
      </AdminTitle>
      <div role="tablist" aria-label="Statut" className="flex flex-wrap gap-1.5">
        {TABS.map((s) => (
          <button
            key={s || "all"}
            role="tab"
            aria-selected={s === status}
            onClick={() => go({ statut: s, page: "" })}
            className="h-9 rounded-full border border-[#cfc8be] bg-white px-3 text-[13px] font-semibold aria-selected:border-encre aria-selected:bg-encre aria-selected:text-porcelaine"
          >
            {s ? ORDER_STATUS[s] : "Toutes"}
          </button>
        ))}
      </div>
      {isLoading && <Loading />}
      {error && <Alert>{errorMessage(error)}</Alert>}
      {data && (
        <>
          <Table head={["N°", "Statut", "Client", "Téléphone", "Commune", "Total", "Paiement", "Livreur", "Reçue"]}>
            {data.items.map((o) => (
              <tr key={o.number}>
                <td className={td}><Link href={`/admin/commandes/${o.number}`} className="font-bold underline-offset-4 hover:underline">{o.number}</Link></td>
                <td className={td}><StatusPill status={o.status} /></td>
                <td className={td}>{o.customer_name}</td>
                <td className={td}><a href={`tel:${o.phone}`}>{formatPhone(o.phone)}</a></td>
                <td className={td}>{o.commune_name}</td>
                <td className={`${td} text-right`}>{formatFCFA(o.total)}</td>
                <td className={td}>{PAYMENT_STATUS[o.payment_status]}</td>
                <td className={td}>{o.courier_name ?? "—"}</td>
                <td className={`${td} text-encre-douce`}>{formatDateTime(o.created_at)}</td>
              </tr>
            ))}
          </Table>
          {data.items.length === 0 && <p className="text-sm text-encre-douce">Aucune commande.</p>}
          <div className="flex items-center gap-4 text-sm">
            <span>{data.total} commande{data.total > 1 ? "s" : ""}</span>
            {page > 1 && <button className="underline" onClick={() => go({ page: String(page - 1) })}>← Précédentes</button>}
            {page * data.page_size < data.total && <button className="underline" onClick={() => go({ page: String(page + 1) })}>Suivantes →</button>}
          </div>
        </>
      )}
    </>
  );
}
