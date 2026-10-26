"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { AdminTitle, Table, td } from "@/components/admin/ui";
import { Alert, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDate, formatFCFA, formatPhone } from "@/lib/format";
import type { Customer, Page } from "@/lib/types";

export default function ClientsPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), ...(q && { q }) });
  const { data, isLoading, error } = useQuery({ queryKey: ["customers", q, page], queryFn: () => api<Page<Customer>>(`/admin/customers?${params}`) });
  return (
    <>
      <AdminTitle>Clients</AdminTitle>
      <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Nom, e-mail ou téléphone" aria-label="Rechercher un client" className={`${inputClass} h-10 max-w-sm`} />
      <p className="text-xs text-encre-douce">Comptes clients uniquement ; les commandes sans compte se retrouvent dans « Commandes ».</p>
      {isLoading && <Loading />}
      {error && <Alert>{errorMessage(error)}</Alert>}
      {data && (
        <>
          <Table head={["Client", "E-mail", "Téléphone", "Inscrit le", "Commandes", "Livré"]}>
            {data.items.map((c) => (
              <tr key={c.id}>
                <td className={td}><Link href={`/admin/clients/${c.id}`} className="font-semibold">{c.full_name}</Link>{!c.is_active && " (désactivé)"}</td>
                <td className={td}>{c.email}</td>
                <td className={td}>{formatPhone(c.phone)}</td>
                <td className={td}>{formatDate(c.created_at)}</td>
                <td className={td}>{c.orders_count}</td>
                <td className={td}>{formatFCFA(c.delivered_total)}</td>
              </tr>
            ))}
          </Table>
          <div className="flex gap-4 text-sm">
            <span>{data.total} client{data.total > 1 ? "s" : ""}</span>
            {page > 1 && <button className="underline" onClick={() => setPage(page - 1)}>← Précédents</button>}
            {page * data.page_size < data.total && <button className="underline" onClick={() => setPage(page + 1)}>Suivants →</button>}
          </div>
        </>
      )}
    </>
  );
}
