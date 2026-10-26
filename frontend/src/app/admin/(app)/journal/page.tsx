"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { OwnerOnly } from "@/components/admin/owner-only";
import { AdminTitle, Table, td } from "@/components/admin/ui";
import { Alert, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AuditEntry, Page } from "@/lib/types";

const compact = (v: Record<string, unknown> | null) =>
  v ? Object.entries(v).map(([k, x]) => `${k} : ${typeof x === "object" ? JSON.stringify(x) : String(x)}`).join(" · ") : "";

export default function JournalPage() {
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), ...(action && { action }) });
  const { data, isLoading, error } = useQuery({ queryKey: ["audit", action, page], queryFn: () => api<Page<AuditEntry>>(`/admin/audit-logs?${params}`) });
  return (
    <OwnerOnly>
      <AdminTitle>Journal d&apos;audit</AdminTitle>
      <select value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} aria-label="Type d'action" className={`${inputClass} h-10 max-w-xs`}>
        <option value="">Toutes les actions</option>
        <option value="order">Commandes</option>
        <option value="variant">Prix et contenances</option>
        <option value="stock">Stock</option>
        <option value="cash">Remises de caisse</option>
        <option value="staff">Collaborateurs</option>
        <option value="product">Produits</option>
        <option value="settings">Paramètres</option>
        <option value="commune">Communes</option>
        <option value="auth">Sécurité</option>
      </select>
      {isLoading && <Loading />}
      {error && <Alert>{errorMessage(error)}</Alert>}
      {data && (
        <>
          <Table head={["Date", "Auteur", "Action", "Objet", "Avant", "Après"]}>
            {data.items.map((e) => (
              <tr key={e.id}>
                <td className={`${td} whitespace-nowrap text-encre-douce`}>{formatDateTime(e.created_at)}</td>
                <td className={td}>{e.author ?? "—"}</td>
                <td className={`${td} font-mono text-xs`}>{e.action}</td>
                <td className={td}>{e.entity_type} {e.entity_id}</td>
                <td className={`${td} text-xs`}>{compact(e.before)}</td>
                <td className={`${td} text-xs`}>{compact(e.after)}</td>
              </tr>
            ))}
          </Table>
          <div className="flex gap-4 text-sm">
            {page > 1 && <button className="underline" onClick={() => setPage(page - 1)}>← Plus récents</button>}
            {page * data.page_size < data.total && <button className="underline" onClick={() => setPage(page + 1)}>Plus anciens →</button>}
          </div>
        </>
      )}
    </OwnerOnly>
  );
}
