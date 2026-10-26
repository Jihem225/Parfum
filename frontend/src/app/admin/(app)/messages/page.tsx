"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AdminTitle } from "@/components/admin/ui";
import { Alert, Button, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime, formatPhone } from "@/lib/format";
import type { ContactMessage, Page } from "@/lib/types";

export default function MessagesPage() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<"NOUVEAU" | "TRAITE" | "">("NOUVEAU");
  const { data, isLoading, error } = useQuery({ queryKey: ["messages", status], queryFn: () => api<Page<ContactMessage>>(`/admin/contact-messages${status ? `?status=${status}` : ""}`) });
  const mark = useMutation({
    mutationFn: (m: ContactMessage) => api(`/admin/contact-messages/${m.id}`, { method: "PATCH", json: { status: m.status === "NOUVEAU" ? "TRAITE" : "NOUVEAU" } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["messages"] }),
  });
  return (
    <>
      <AdminTitle>Messages</AdminTitle>
      <div className="flex gap-2 text-sm">
        {([["NOUVEAU", "À traiter"], ["TRAITE", "Traités"], ["", "Tous"]] as const).map(([s, l]) => (
          <button key={s} onClick={() => setStatus(s)} aria-pressed={status === s} className="h-9 rounded-full border border-[#cfc8be] bg-white px-3 font-semibold aria-pressed:bg-encre aria-pressed:text-porcelaine">{l}</button>
        ))}
      </div>
      {isLoading && <Loading />}
      {(error ?? mark.error) && <Alert>{errorMessage(error ?? mark.error)}</Alert>}
      <ul className="flex flex-col gap-3">
        {data?.items.map((m) => (
          <li key={m.id} className="flex flex-col gap-2 rounded border border-filet bg-white p-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <strong>{m.name}</strong>
              {m.phone && <a href={`tel:${m.phone}`}>{formatPhone(m.phone)}</a>}
              {m.email && <a href={`mailto:${m.email}`}>{m.email}</a>}
              <span className="text-encre-douce">{formatDateTime(m.created_at)}</span>
              <Button size="sm" variant="secondary" className="ml-auto" onClick={() => mark.mutate(m)}>{m.status === "NOUVEAU" ? "Marquer traité" : "Remettre à traiter"}</Button>
            </div>
            <p className="whitespace-pre-line">{m.message}</p>
          </li>
        ))}
        {data?.items.length === 0 && <li className="text-encre-douce">Aucun message.</li>}
      </ul>
    </>
  );
}
