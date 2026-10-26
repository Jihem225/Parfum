"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AdminTitle, Table, td } from "@/components/admin/ui";
import { Alert, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime, MOVEMENT } from "@/lib/format";
import type { Movement, Page } from "@/lib/types";

const signed = (n: number) => (n > 0 ? `+${n}` : n === 0 ? "—" : String(n));

export default function MouvementsPage() {
  const variantId = useSearchParams().get("variant_id");
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), ...(variantId && { variant_id: variantId }) });
  const { data, isLoading, error } = useQuery({ queryKey: ["movements", variantId, page], queryFn: () => api<Page<Movement>>(`/admin/stock/movements?${params}`) });
  return (
    <>
      <Link href="/admin/stock" className="text-sm underline underline-offset-4">← Stock</Link>
      <AdminTitle>Mouvements de stock</AdminTitle>
      {isLoading && <Loading />}
      {error && <Alert>{errorMessage(error)}</Alert>}
      {data && (
        <>
          <Table head={["Date", "Parfum", "Type", "Physique", "Réservé", "Motif", "Commande", "Auteur"]}>
            {data.items.map((m) => (
              <tr key={m.id}>
                <td className={`${td} text-encre-douce`}>{formatDateTime(m.created_at)}</td>
                <td className={td}>{m.product_name} {m.volume_ml} ml</td>
                <td className={td}>{MOVEMENT[m.type]}</td>
                <td className={td}>{signed(m.delta_physical)}</td>
                <td className={td}>{signed(m.delta_reserved)}</td>
                <td className={td}>{m.reason ?? ""}</td>
                <td className={td}>{m.order_number && <Link href={`/admin/commandes/${m.order_number}`} className="underline">{m.order_number}</Link>}</td>
                <td className={td}>{m.author ?? "—"}</td>
              </tr>
            ))}
          </Table>
          <div className="flex gap-4 text-sm">
            {page > 1 && <button className="underline" onClick={() => setPage(page - 1)}>← Plus récents</button>}
            {page * data.page_size < data.total && <button className="underline" onClick={() => setPage(page + 1)}>Plus anciens →</button>}
          </div>
        </>
      )}
    </>
  );
}
