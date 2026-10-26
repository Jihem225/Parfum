"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AdminTitle, Card, Table, td } from "@/components/admin/ui";
import { Alert, Button, Field, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import type { StockRow } from "@/lib/types";

export default function StockPage() {
  const qc = useQueryClient();
  const [lowOnly, setLowOnly] = useState(useSearchParams().get("bas") === "1");
  const [q, setQ] = useState("");
  const params = new URLSearchParams({ ...(lowOnly && { low_only: "true" }), ...(q && { q }) });
  const rows = useQuery({ queryKey: ["stock", lowOnly, q], queryFn: () => api<StockRow[]>(`/admin/stock?${params}`) });
  const [target, setTarget] = useState<StockRow | null>(null);
  const [form, setForm] = useState({ type: "ENTREE", quantity: "", reason: "" });
  const move = useMutation({
    mutationFn: () => api<StockRow>("/admin/stock/movements", { json: { variant_id: target?.variant_id, type: form.type, quantity: Number(form.quantity), reason: form.reason } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stock"] });
      setTarget(null);
      setForm({ type: "ENTREE", quantity: "", reason: "" });
    },
  });
  return (
    <>
      <AdminTitle actions={<Link href="/admin/stock/mouvements" className="text-sm underline underline-offset-4">Historique des mouvements</Link>}>Stock</AdminTitle>
      <div className="flex flex-wrap items-center gap-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Parfum ou SKU" aria-label="Rechercher" className={`${inputClass} h-10 max-w-xs`} />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={lowOnly} onChange={(e) => setLowOnly(e.target.checked)} className="h-5 w-5" />Stock bas uniquement</label>
      </div>
      {target && (
        <Card title={`${target.product_name} ${target.volume_ml} ml — physique ${target.stock_physical}, réservé ${target.stock_reserved}`}>
          <form className="grid gap-3 md:grid-cols-4 md:items-end" onSubmit={(e) => { e.preventDefault(); move.mutate(); }}>
            <Field label="Mouvement">
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className={inputClass}>
                <option value="ENTREE">Entrée (réception)</option>
                <option value="AJUSTEMENT">Ajustement (+ ou −)</option>
              </select>
            </Field>
            <Field label="Quantité" hint={form.type === "AJUSTEMENT" ? "Négative pour retirer (casse, inventaire)." : undefined}>
              <input type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required className={inputClass} />
            </Field>
            <Field label={form.type === "AJUSTEMENT" ? "Motif (obligatoire)" : "Référence (facultatif)"}>
              <input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} required={form.type === "AJUSTEMENT"} maxLength={255} className={inputClass} />
            </Field>
            <div className="flex gap-2">
              <Button type="submit" disabled={move.isPending}>Enregistrer</Button>
              <Button variant="ghost" onClick={() => setTarget(null)}>Fermer</Button>
            </div>
          </form>
          {move.isError && <Alert>{errorMessage(move.error)}</Alert>}
        </Card>
      )}
      {rows.isLoading && <Loading />}
      {rows.error && <Alert>{errorMessage(rows.error)}</Alert>}
      {rows.data && (
        <Table head={["Parfum", "SKU", "Physique", "Réservé", "Disponible", "Seuil", ""]}>
          {rows.data.map((r) => (
            <tr key={r.variant_id} className={r.is_low ? "bg-[#fbf3e8]" : ""}>
              <td className={td}><Link href={`/admin/produits/${r.product_id}`} className="font-semibold">{r.product_name}</Link> {r.volume_ml} ml{!r.is_active && <span className="text-encre-douce"> (inactive)</span>}</td>
              <td className={`${td} font-mono`}>{r.sku}</td>
              <td className={td}>{r.stock_physical}</td>
              <td className={td}>{r.stock_reserved}</td>
              <td className={`${td} font-bold ${r.is_low ? "text-safran" : ""}`}>{r.available}{r.is_low && " · bas"}</td>
              <td className={td}>{r.low_stock_threshold}</td>
              <td className={td}>
                <div className="flex gap-3">
                  <Button size="sm" variant="secondary" onClick={() => setTarget(r)}>Mouvement</Button>
                  <Link href={`/admin/stock/mouvements?variant_id=${r.variant_id}`} className="self-center text-sm underline">Historique</Link>
                </div>
              </td>
            </tr>
          ))}
        </Table>
      )}
    </>
  );
}
