"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { AdminTitle, Table, td } from "@/components/admin/ui";
import { ProductImage } from "@/components/product-image";
import { Alert, buttonClass, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatFCFA, PRODUCT_STATUS } from "@/lib/format";
import type { AdminProductRow, ProductStatus } from "@/lib/types";

export default function ProduitsPage() {
  const [status, setStatus] = useState<ProductStatus | "">("");
  const [q, setQ] = useState("");
  const params = new URLSearchParams({ ...(status && { status }), ...(q && { q }) });
  const { data, isLoading, error } = useQuery({ queryKey: ["admin-products", status, q], queryFn: () => api<AdminProductRow[]>(`/admin/products?${params}`) });
  return (
    <>
      <AdminTitle actions={<Link href="/admin/produits/nouveau" className={buttonClass("primary", "sm")}>Nouveau parfum</Link>}>Produits</AdminTitle>
      <div className="flex flex-wrap gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nom ou SKU" aria-label="Rechercher" className={`${inputClass} h-10 max-w-xs`} />
        <select value={status} onChange={(e) => setStatus(e.target.value as ProductStatus | "")} aria-label="Statut" className={`${inputClass} h-10 max-w-48`}>
          <option value="">Tous les statuts</option>
          {Object.entries(PRODUCT_STATUS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </div>
      {isLoading && <Loading />}
      {error && <Alert>{errorMessage(error)}</Alert>}
      {data && (
        <Table head={["", "Parfum", "Collection", "Statut", "Contenances", "Prix", "Disponible"]}>
          {data.map((p) => (
            <tr key={p.id}>
              <td className={td}><ProductImage image={p.image} productId={p.id} name={p.name} className="h-12 w-10" /></td>
              <td className={td}><Link href={`/admin/produits/${p.id}`} className="font-semibold underline-offset-4 hover:underline">{p.name}</Link></td>
              <td className={td}>{p.collection.name}</td>
              <td className={td}>{PRODUCT_STATUS[p.status]}</td>
              <td className={td}>{p.volumes.map((v) => `${v} ml`).join(", ") || "—"}</td>
              <td className={td}>{p.min_price === null ? "—" : p.min_price === p.max_price ? formatFCFA(p.min_price) : `${formatFCFA(p.min_price)} – ${formatFCFA(p.max_price ?? 0)}`}</td>
              <td className={`${td} ${p.available === 0 ? "font-semibold text-erreur" : ""}`}>{p.available}</td>
            </tr>
          ))}
        </Table>
      )}
    </>
  );
}
