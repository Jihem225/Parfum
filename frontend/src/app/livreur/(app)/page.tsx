"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Alert, Button, Field, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { FAILURE_REASON, formatFCFA, formatPhone } from "@/lib/format";
import type { Delivery, FailureReason } from "@/lib/types";

function DeliveryCard({ d }: { d: Delivery }) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"" | "delivered" | "failed">("");
  const [cashOk, setCashOk] = useState(false);
  const [reason, setReason] = useState<FailureReason>("INJOIGNABLE");
  const [note, setNote] = useState("");
  const refresh = () => qc.invalidateQueries({ queryKey: ["deliveries"] });
  const delivered = useMutation({
    mutationFn: () => api(`/courier/deliveries/${d.number}/delivered`, { json: { amount_collected: d.amount_to_collect } }),
    onSuccess: refresh,
  });
  const failed = useMutation({ mutationFn: () => api(`/courier/deliveries/${d.number}/failed`, { json: { reason, note } }), onSuccess: refresh });
  const failure = delivered.error ?? failed.error;
  const prepaid = d.amount_to_collect === 0; // payée par mobile money
  return (
    <li className="flex flex-col gap-3 rounded border border-filet bg-white p-4">
      <div className="flex items-baseline justify-between">
        <strong className="text-lg">{d.customer_name}</strong>
        <span className="text-sm text-encre-douce">{d.number}{d.delivery_attempts > 1 && ` · tentative ${d.delivery_attempts}`}</span>
      </div>
      <a href={`tel:${d.phone}`} className="flex h-12 items-center justify-center gap-2 rounded-[2px] border border-encre text-base font-bold text-encre">
        Appeler {formatPhone(d.phone)}
      </a>
      <div className="text-[15px]">
        <strong>{d.commune_name}</strong> — {d.address_line}
        {d.landmark && <div className="text-encre-douce">Repère : {d.landmark}</div>}
      </div>
      <div className="text-sm text-encre-douce">{d.items.map((i) => `${i.quantity} × ${i.product_name} ${i.volume_ml} ml`).join(" · ")}</div>
      {prepaid ? (
        <div className="bg-surface px-3 py-3 text-lg font-bold">Déjà payée · rien à encaisser</div>
      ) : (
        <div className="flex items-center justify-between bg-surface px-3 py-3 text-lg font-bold">
          <span>À encaisser</span><span>{formatFCFA(d.amount_to_collect)}</span>
        </div>
      )}
      {failure && <Alert>{errorMessage(failure)}</Alert>}
      {mode === "" && (
        <div className="grid grid-cols-2 gap-2">
          <Button onClick={() => setMode("delivered")}>Livrée</Button>
          <Button variant="secondary" onClick={() => setMode("failed")}>Échec</Button>
        </div>
      )}
      {mode === "delivered" && prepaid && (
        <div className="grid grid-cols-2 gap-2">
          <Button disabled={delivered.isPending} onClick={() => delivered.mutate()}>Confirmer la remise</Button>
          <Button variant="ghost" onClick={() => setMode("")}>Retour</Button>
        </div>
      )}
      {mode === "delivered" && !prepaid && (
        <div className="flex flex-col gap-3">
          {/* RG-43 : « livrée » exige de confirmer l'encaissement du montant exact. */}
          <label className="flex items-start gap-3 text-[15px]">
            <input type="checkbox" checked={cashOk} onChange={(e) => setCashOk(e.target.checked)} className="mt-0.5 h-6 w-6 flex-none" />
            <span>J&apos;ai reçu <strong>{formatFCFA(d.amount_to_collect)}</strong> en espèces.</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <Button disabled={!cashOk || delivered.isPending} onClick={() => delivered.mutate()}>Livrée et encaissée</Button>
            <Button variant="ghost" onClick={() => setMode("")}>Retour</Button>
          </div>
        </div>
      )}
      {mode === "failed" && (
        <div className="flex flex-col gap-3">
          <Field label="Motif">
            <select value={reason} onChange={(e) => setReason(e.target.value as FailureReason)} className={inputClass}>
              {Object.entries(FAILURE_REASON).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <Field label="Précision (facultatif)"><input value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} className={inputClass} /></Field>
          <div className="grid grid-cols-2 gap-2">
            <Button variant="danger" disabled={failed.isPending} onClick={() => failed.mutate()}>Déclarer l&apos;échec</Button>
            <Button variant="ghost" onClick={() => setMode("")}>Retour</Button>
          </div>
        </div>
      )}
    </li>
  );
}

export default function LivraisonsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["deliveries"], queryFn: () => api<Delivery[]>("/courier/deliveries"), refetchInterval: 60_000 });
  if (isLoading) return <Loading />;
  if (error) return <Alert>{errorMessage(error)}</Alert>;
  const total = data?.reduce((s, d) => s + d.amount_to_collect, 0) ?? 0;
  return (
    <>
      <h1 className="font-display text-[28px]">Mes livraisons</h1>
      {data?.length ? (
        <p className="text-sm text-encre-douce">{data.length} colis · {formatFCFA(total)} à encaisser au total</p>
      ) : (
        <Alert tone="info">Aucune livraison en cours. Les nouveaux colis apparaissent ici.</Alert>
      )}
      <ul className="flex flex-col gap-4">{data?.map((d) => <DeliveryCard key={d.number} d={d} />)}</ul>
    </>
  );
}
