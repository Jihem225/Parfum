"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { AdminTitle, Card, Table, td } from "@/components/admin/ui";
import { Alert, Button, Field, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime, formatFCFA } from "@/lib/format";
import type { Page, PendingCash, Remittance } from "@/lib/types";

function RemitForm({ pending }: { pending: PendingCash }) {
  const qc = useQueryClient();
  const [received, setReceived] = useState(String(pending.amount));
  const [note, setNote] = useState("");
  const difference = Number(received) - pending.amount;
  const remit = useMutation({
    mutationFn: () => api<Remittance>("/admin/remittances", { json: { courier_id: pending.courier.id, expected_amount: pending.amount, received_amount: Number(received), note } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cash"] }),
    onError: () => qc.invalidateQueries({ queryKey: ["cash", "pending"] }), // montant attendu peut-être changé
  });
  return (
    <Card title={`${pending.courier.full_name} · ${formatFCFA(pending.amount)} à remettre`}>
      <ul className="flex flex-wrap gap-2 text-xs">
        {pending.orders.map((o) => <li key={o.number}><Link href={`/admin/commandes/${o.number}`} className="rounded bg-surface px-2 py-1">{o.number} · {formatFCFA(o.amount)}</Link></li>)}
      </ul>
      <form className="grid gap-3 md:grid-cols-3 md:items-end" onSubmit={(e) => { e.preventDefault(); if (window.confirm("Enregistrer cette remise ? Elle ne pourra plus être modifiée.")) remit.mutate(); }}>
        <Field label="Montant reçu (FCFA)"><input type="number" min={0} value={received} onChange={(e) => setReceived(e.target.value)} required className={inputClass} /></Field>
        <Field label={difference ? "Explication de l'écart (obligatoire)" : "Note"}><input value={note} onChange={(e) => setNote(e.target.value)} required={difference !== 0} maxLength={500} className={inputClass} /></Field>
        <Button type="submit" disabled={remit.isPending}>Enregistrer la remise</Button>
      </form>
      {difference !== 0 && <p className={`text-sm font-semibold ${difference < 0 ? "text-erreur" : "text-safran"}`}>Écart : {difference > 0 ? "+" : ""}{formatFCFA(difference)}</p>}
      {remit.isError && <Alert>{errorMessage(remit.error)}</Alert>}
    </Card>
  );
}

export default function EncaissementsPage() {
  const pending = useQuery({ queryKey: ["cash", "pending"], queryFn: () => api<PendingCash[]>("/admin/couriers/pending-cash") });
  const history = useQuery({ queryKey: ["cash", "history"], queryFn: () => api<Page<Remittance>>("/admin/remittances") });
  return (
    <>
      <AdminTitle>Encaissements</AdminTitle>
      <p className="text-sm text-encre-douce">Le montant attendu est calculé automatiquement. Une remise enregistrée ne se modifie plus.</p>
      {pending.isLoading && <Loading />}
      {pending.error && <Alert>{errorMessage(pending.error)}</Alert>}
      {pending.data?.length === 0 && <Alert tone="success">Aucun livreur ne détient d&apos;espèces à remettre.</Alert>}
      {pending.data?.map((p) => <RemitForm key={`${p.courier.id}-${p.amount}`} pending={p} />)}
      <h2 className="mt-4 text-lg font-bold">Remises enregistrées</h2>
      {history.data && (
        <Table head={["Date", "Livreur", "Attendu", "Reçu", "Écart", "Reçu par", "Commandes", "Note"]}>
          {history.data.items.map((r) => (
            <tr key={r.id}>
              <td className={`${td} text-encre-douce`}>{formatDateTime(r.created_at)}</td>
              <td className={td}>{r.courier.full_name}</td>
              <td className={td}>{formatFCFA(r.expected_amount)}</td>
              <td className={td}>{formatFCFA(r.received_amount)}</td>
              <td className={`${td} font-bold ${r.difference < 0 ? "text-erreur" : ""}`}>{r.difference ? formatFCFA(r.difference) : "—"}</td>
              <td className={td}>{r.received_by.full_name}</td>
              <td className={td}>{r.order_numbers.join(", ")}</td>
              <td className={td}>{r.note ?? ""}</td>
            </tr>
          ))}
        </Table>
      )}
    </>
  );
}
