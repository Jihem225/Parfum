"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AdminTitle } from "@/components/admin/ui";
import { Alert, Button, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { EmailStatus, OutboxEmail, Page } from "@/lib/types";

const TABS: [EmailStatus, string][] = [
  ["FAILED", "En échec"],
  ["PENDING", "En attente"],
  ["SENT", "Envoyés"],
];

/** File d'envoi : les e-mails abandonnés après 6 essais se renvoient d'ici. */
export default function EmailsPage() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<EmailStatus>("FAILED");
  const { data, isLoading, error } = useQuery({
    queryKey: ["emails", status],
    queryFn: () => api<Page<OutboxEmail>>(`/admin/emails?status=${status}`),
    refetchInterval: 5000, // la file avance toute seule (envoi toutes les 5 secondes)
  });
  const retry = useMutation({
    mutationFn: (id: number) => api<OutboxEmail>(`/admin/emails/${id}/retry`, { json: {} }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["emails"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
  return (
    <>
      <AdminTitle>E-mails</AdminTitle>
      <p className="text-sm text-encre-douce">
        Chaque e-mail est réessayé automatiquement pendant environ 4 heures. Au-delà, il passe « en échec » : corrigez la cause (adresse,
        configuration), puis renvoyez-le. Les envoyés sont effacés après 30 jours.
      </p>
      <div className="flex gap-2 text-sm">
        {TABS.map(([s, l]) => (
          <button key={s} onClick={() => setStatus(s)} aria-pressed={status === s} className="h-9 rounded-full border border-[#cfc8be] bg-white px-3 font-semibold aria-pressed:bg-encre aria-pressed:text-porcelaine">{l}</button>
        ))}
      </div>
      {isLoading && <Loading />}
      {(error ?? retry.error) && <Alert>{errorMessage(error ?? retry.error)}</Alert>}
      <ul className="flex flex-col gap-3">
        {data?.items.map((m) => (
          <li key={m.id} className="flex flex-col gap-2 rounded border border-filet bg-white p-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <strong>{m.subject}</strong>
              <span>{m.to_address}</span>
              <span className="text-encre-douce">{formatDateTime(m.created_at)}</span>
              {m.status === "FAILED" && (
                <Button size="sm" variant="secondary" className="ml-auto" disabled={retry.isPending} onClick={() => retry.mutate(m.id)}>Renvoyer</Button>
              )}
            </div>
            <div className="text-encre-douce">
              {m.status === "SENT" && m.sent_at && `Envoyé le ${formatDateTime(m.sent_at)}`}
              {m.status === "PENDING" && (m.attempts ? `${m.attempts} essai(s), prochain le ${formatDateTime(m.next_attempt_at)}` : "Envoi imminent")}
              {m.status === "FAILED" && `${m.attempts} essai(s)`}
            </div>
            {m.last_error && <p className="break-words font-mono text-xs text-erreur">{m.last_error}</p>}
          </li>
        ))}
        {data?.items.length === 0 && <li className="text-encre-douce">{status === "FAILED" ? "Aucun e-mail en échec." : "Aucun e-mail."}</li>}
      </ul>
    </>
  );
}
