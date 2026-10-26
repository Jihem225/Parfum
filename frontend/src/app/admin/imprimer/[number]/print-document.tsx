"use client";

import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime, formatFCFA, formatPhone } from "@/lib/format";
import type { AdminOrder } from "@/lib/types";

/** Bon de préparation (articles, SKU) ou bordereau de livraison (client, adresse, montant). */
export function PrintDocument({ number, doc }: { number: string; doc: "bon" | "bordereau" }) {
  const { data: o, isLoading, error } = useQuery({ queryKey: ["admin-order", number], queryFn: () => api<AdminOrder>(`/admin/orders/${number}`) });
  if (isLoading) return <Loading />;
  if (error || !o) return <Alert>{errorMessage(error)}</Alert>;
  return (
    <div className="flex flex-col gap-5 text-[15px]">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-display tracking-[0.2em]">PROJET PARFUMS</div>
          <h1 className="text-2xl font-bold">{doc === "bon" ? "Bon de préparation" : "Bordereau de livraison"}</h1>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold">{o.number}</div>
          <div className="text-sm">{formatDateTime(o.created_at)}</div>
        </div>
      </div>
      {doc === "bon" ? (
        <table className="w-full border-collapse text-left">
          <thead><tr className="border-b-2 border-encre"><th className="py-2">Article</th><th>Contenance</th><th>SKU</th><th className="text-right">Qté</th><th className="w-10 text-center">✓</th></tr></thead>
          <tbody>
            {o.items.map((i) => (
              <tr key={i.variant_id} className="border-b border-filet">
                <td className="py-3">{i.product_name}</td><td>{i.volume_ml} ml</td><td className="font-mono">{i.sku}</td>
                <td className="text-right text-lg font-bold">{i.quantity}</td><td className="text-center">☐</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="border-2 border-encre p-4">
            <div className="text-xl font-bold">{o.customer_name}</div>
            <div className="text-xl">{formatPhone(o.phone)}</div>
            <div className="mt-2"><strong>{o.commune_name}</strong> — {o.address_line}</div>
            {o.landmark && <div>Repère : {o.landmark}</div>}
          </div>
          <div className="text-sm">{o.items.map((i) => `${i.quantity} × ${i.product_name} ${i.volume_ml} ml`).join(" · ")}</div>
          <div className="flex items-center justify-between border-2 border-encre p-4 text-xl font-bold">
            {o.payment_method === "MOBILE_MONEY" ? (
              <><span>Déjà payée · rien à encaisser</span><span>{formatFCFA(0)}</span></>
            ) : (
              <><span>À encaisser en espèces</span><span>{formatFCFA(o.total)}</span></>
            )}
          </div>
          {o.courier && <div>Livreur : {o.courier.full_name}</div>}
        </div>
      )}
      <Button className="no-print" onClick={() => window.print()}>Imprimer</Button>
    </div>
  );
}
