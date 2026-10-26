"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Card } from "@/components/admin/ui";
import { Alert, Button, buttonClass, Field, inputClass, Loading, StatusPill } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { FAILURE_REASON, formatDateTime, formatFCFA, formatPhone, ORDER_STATUS, PAYMENT_STATUS } from "@/lib/format";
import { useMe } from "@/lib/hooks";
import type { AdminOrder, CallResult, FailureReason, OrderStatus } from "@/lib/types";

const CALLS: [CallResult, string][] = [
  ["CONFIRMEE", "Confirmée"],
  ["PAS_DE_REPONSE", "Pas de réponse"],
  ["ANNULATION_DEMANDEE", "Le client annule"],
];

export default function CommandeDetailPage() {
  const { number } = useParams<{ number: string }>();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const key = ["admin-order", number];
  const order = useQuery({ queryKey: key, queryFn: () => api<AdminOrder>(`/admin/orders/${number}`) });
  const couriers = useQuery({ queryKey: ["couriers"], queryFn: () => api<{ id: number; full_name: string; phone: string }[]>("/admin/couriers") });
  const [note, setNote] = useState("");
  const [courier, setCourier] = useState("");
  const [reason, setReason] = useState<FailureReason>("INJOIGNABLE");
  const done = (o: AdminOrder) => {
    qc.setQueryData(key, o);
    qc.invalidateQueries({ queryKey: ["admin-orders"] });
    setNote("");
  };
  const call = useMutation({ mutationFn: (result: CallResult) => api<AdminOrder>(`/admin/orders/${number}/calls`, { json: { result, note } }), onSuccess: done });
  const move = useMutation({
    mutationFn: (to: OrderStatus) => api<AdminOrder>(`/admin/orders/${number}/transition`, { json: { to, note, courier_id: courier ? Number(courier) : null } }),
    onSuccess: done,
  });
  // Livrée / échec passent par les routes du livreur (le back-office peut agir pour lui).
  const delivered = useMutation({
    mutationFn: (amount: number) => api(`/courier/deliveries/${number}/delivered`, { json: { amount_collected: amount } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const failed = useMutation({
    mutationFn: () => api(`/courier/deliveries/${number}/failed`, { json: { reason, note } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
  const failure = call.error ?? move.error ?? delivered.error ?? failed.error;

  if (order.isLoading) return <Loading />;
  if (order.error || !order.data) return <Alert>{errorMessage(order.error)}</Alert>;
  const o = order.data;
  const cancellable = ["EN_ATTENTE_CONFIRMATION", "CONFIRMEE", "EN_PREPARATION"].includes(o.status);
  const cancel = () => {
    if (!note.trim()) return window.alert("Indiquez le motif de l'annulation dans la note.");
    if (window.confirm(`Annuler la commande ${o.number} ? Le stock sera libéré.`)) move.mutate("ANNULEE");
  };
  const courierPicker = (
    <Field label="Livreur">
      <select value={courier} onChange={(e) => setCourier(e.target.value)} className={inputClass}>
        <option value="">Choisir un livreur</option>
        {couriers.data?.map((c) => <option key={c.id} value={c.id}>{c.full_name} · {formatPhone(c.phone)}</option>)}
      </select>
    </Field>
  );

  return (
    <>
      <Link href="/admin/commandes" className="no-print text-sm underline underline-offset-4">← Commandes</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold tracking-[0.02em]">{o.number}</h1>
        <StatusPill status={o.status} />
        <span className="text-sm text-encre-douce">Paiement : {PAYMENT_STATUS[o.payment_status]}</span>
        <div className="no-print ml-auto flex gap-2">
          <Link href={`/admin/imprimer/${o.number}?doc=bon`} target="_blank" className={buttonClass("secondary", "sm")}>Bon de préparation</Link>
          <Link href={`/admin/imprimer/${o.number}?doc=bordereau`} target="_blank" className={buttonClass("secondary", "sm")}>Bordereau</Link>
        </div>
      </div>
      <p className="text-sm text-encre-douce">Reçue le {formatDateTime(o.created_at)} · {o.user_id ? "client avec compte" : "invité"}</p>
      {o.should_cancel && <Alert tone="info">3 appels sans réponse : cette commande peut être annulée (RG-31).</Alert>}
      {failure && <Alert>{errorMessage(failure)}</Alert>}

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <div className="flex flex-col gap-4">
          <Card title="Client et livraison">
            <div className="grid gap-4 text-sm md:grid-cols-2">
              <div className="flex flex-col gap-1">
                <strong>{o.customer_name}</strong>
                <a href={`tel:${o.phone}`} className="font-bold">{formatPhone(o.phone)}</a>
                {o.email && <span>{o.email}</span>}
              </div>
              <div className="flex flex-col gap-1">
                <span><strong>{o.commune_name}</strong> · {formatFCFA(o.delivery_fee)} · {o.delivery_delay_label}</span>
                <span>{o.address_line}</span>
                {o.landmark && <span className="text-encre-douce">Repère : {o.landmark}</span>}
                {o.courier && <span>Livreur : {o.courier.full_name} · tentative {o.delivery_attempts}</span>}
              </div>
            </div>
          </Card>
          <Card title="Articles">
            <div className="flex flex-col gap-2 text-sm">
              {o.items.map((i) => (
                <div key={i.variant_id} className="flex justify-between gap-3">
                  <span>{i.product_name} · {i.volume_ml} ml × {i.quantity} <span className="text-encre-douce">{i.sku}</span></span>
                  <span>{formatFCFA(i.line_total)}</span>
                </div>
              ))}
              <div className="flex justify-between text-encre-douce"><span>Livraison</span><span>{formatFCFA(o.delivery_fee)}</span></div>
              <div className="flex justify-between border-t border-filet pt-2 font-bold"><span>Total · espèces à encaisser</span><span>{formatFCFA(o.total)}</span></div>
            </div>
          </Card>
          <Card title="Historique">
            <ol className="flex flex-col gap-2 text-sm">
              {o.events.map((e, i) => (
                <li key={i} className="flex flex-wrap gap-x-2">
                  <span className="text-encre-douce">{formatDateTime(e.at)}</span>
                  <span className="font-semibold">
                    {e.kind === "CALL" ? `Appel : ${CALLS.find(([c]) => c === e.call_result)?.[1] ?? e.call_result}` : e.to_status ? ORDER_STATUS[e.to_status] : e.kind}
                  </span>
                  {e.failure_reason && <span>({FAILURE_REASON[e.failure_reason]})</span>}
                  {e.note && <span>— {e.note}</span>}
                  {e.author && <span className="text-encre-douce">· {e.author}</span>}
                </li>
              ))}
            </ol>
          </Card>
        </div>

        <div className="no-print flex flex-col gap-4">
          <Card title="Actions">
            <Field label="Note ou motif" hint="Obligatoire pour une annulation.">
              <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={500} className={`${inputClass} h-auto py-2`} />
            </Field>
            {o.status === "EN_ATTENTE_CONFIRMATION" && (
              <div className="flex flex-col gap-2">
                <span className="text-sm font-semibold">Appel de confirmation · {o.unanswered_calls} sans réponse</span>
                <div className="flex flex-wrap gap-2">
                  {CALLS.map(([r, label]) => (
                    <Button key={r} size="sm" variant={r === "CONFIRMEE" ? "primary" : "secondary"} disabled={call.isPending} onClick={() => call.mutate(r)}>{label}</Button>
                  ))}
                </div>
              </div>
            )}
            {o.status === "CONFIRMEE" && <Button onClick={() => move.mutate("EN_PREPARATION")} disabled={move.isPending}>Passer en préparation</Button>}
            {(o.status === "EN_PREPARATION" || o.status === "ECHEC_LIVRAISON") && (
              <>
                {courierPicker}
                <Button onClick={() => move.mutate("EN_LIVRAISON")} disabled={!courier || move.isPending}>
                  {o.status === "ECHEC_LIVRAISON" ? "Nouvelle tentative de livraison" : "Confier au livreur"}
                </Button>
              </>
            )}
            {o.status === "EN_LIVRAISON" && (
              <>
                <Button
                  disabled={delivered.isPending}
                  onClick={() => window.confirm(`Le livreur a bien encaissé ${formatFCFA(o.total)} ?`) && delivered.mutate(o.total)}
                >
                  Livrée et encaissée
                </Button>
                <Field label="Motif de l'échec">
                  <select value={reason} onChange={(e) => setReason(e.target.value as FailureReason)} className={inputClass}>
                    {Object.entries(FAILURE_REASON).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </Field>
                <Button variant="secondary" disabled={failed.isPending} onClick={() => failed.mutate()}>Déclarer un échec</Button>
              </>
            )}
            {cancellable && <Button variant="danger" onClick={cancel} disabled={move.isPending}>Annuler la commande</Button>}
          </Card>
          {(o.status === "ECHEC_LIVRAISON" || (o.status === "LIVREE" && me?.role === "OWNER")) && (
            <ReturnForm order={o} onDone={done} />
          )}
        </div>
      </div>
    </>
  );
}

/** Colis revenu (contrôle article par article) ou retour d'une commande livrée avec remboursement. */
function ReturnForm({ order, onDone }: { order: AdminOrder; onDone: (o: AdminOrder) => void }) {
  const delivered = order.status === "LIVREE";
  const [lines, setLines] = useState(() => Object.fromEntries(order.items.map((i) => [i.variant_id, { restocked: i.quantity, lost: 0 }])));
  const [note, setNote] = useState("");
  const [refund, setRefund] = useState(String(order.subtotal));
  const submit = useMutation({
    mutationFn: () =>
      api<AdminOrder>(`/admin/orders/${order.number}/return`, {
        json: {
          items: Object.entries(lines).map(([variant_id, v]) => ({ variant_id: Number(variant_id), ...v })),
          note,
          refund_amount: delivered ? Number(refund) : null,
        },
      }),
    onSuccess: onDone,
  });
  return (
    <Card title={delivered ? "Retour client et remboursement" : "Colis revenu à la boutique"}>
      <p className="text-sm text-encre-douce">Pour chaque article : combien reviennent en stock, combien sont abîmés.</p>
      {order.items.map((i) => {
        const line = lines[i.variant_id] ?? { restocked: 0, lost: 0 };
        const set = (k: "restocked" | "lost", v: number) => setLines({ ...lines, [i.variant_id]: { ...line, [k]: v } });
        return (
          <div key={i.variant_id} className="flex flex-col gap-1 text-sm">
            <span className="font-semibold">{i.product_name} {i.volume_ml} ml × {i.quantity}</span>
            <div className="flex gap-2">
              <label className="flex flex-1 flex-col">En stock<input type="number" min={0} max={i.quantity} value={line.restocked} onChange={(e) => set("restocked", Number(e.target.value))} className={`${inputClass} h-10`} /></label>
              <label className="flex flex-1 flex-col">Perdus<input type="number" min={0} max={i.quantity} value={line.lost} onChange={(e) => set("lost", Number(e.target.value))} className={`${inputClass} h-10`} /></label>
            </div>
          </div>
        );
      })}
      <Field label="Note"><input value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} className={inputClass} /></Field>
      {delivered && (
        <Field label="Montant remboursé en espèces (FCFA)">
          <input type="number" min={0} max={order.total} value={refund} onChange={(e) => setRefund(e.target.value)} className={inputClass} />
        </Field>
      )}
      {submit.isError && <Alert>{errorMessage(submit.error)}</Alert>}
      <Button variant="secondary" disabled={submit.isPending} onClick={() => window.confirm("Enregistrer ce retour ? Cette action est définitive.") && submit.mutate()}>
        Enregistrer le retour
      </Button>
    </Card>
  );
}
