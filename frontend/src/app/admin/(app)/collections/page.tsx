"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AdminTitle, Card } from "@/components/admin/ui";
import { Alert, Button, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import type { Collection, Family } from "@/lib/types";

/** Collections et familles olfactives : même gestion (nom, ordre, suppression si inutilisée). */
function Taxons<T extends Collection | Family>({ kind, title }: { kind: "collections" | "families"; title: string }) {
  const qc = useQueryClient();
  const key = [`admin-${kind}`];
  const list = useQuery({ queryKey: key, queryFn: () => api<T[]>(`/admin/${kind}`) });
  const [name, setName] = useState("");
  const refresh = () => qc.invalidateQueries({ queryKey: key });
  const create = useMutation({ mutationFn: () => api(`/admin/${kind}`, { json: { name } }), onSuccess: () => { setName(""); refresh(); } });
  const update = useMutation({ mutationFn: ({ id, ...v }: { id: number } & Record<string, unknown>) => api(`/admin/${kind}/${id}`, { method: "PATCH", json: v }), onSuccess: refresh });
  const remove = useMutation({ mutationFn: (id: number) => api(`/admin/${kind}/${id}`, { method: "DELETE" }), onSuccess: refresh });
  const failure = create.error ?? update.error ?? remove.error;
  return (
    <Card title={title}>
      {failure && <Alert>{errorMessage(failure)}</Alert>}
      <ul className="flex flex-col divide-y divide-filet text-sm">
        {list.data?.map((t) => (
          <li key={t.id} className="flex flex-wrap items-center gap-3 py-2">
            <input defaultValue={t.name} aria-label="Nom" className={`${inputClass} h-9 max-w-60`} onBlur={(e) => e.target.value !== t.name && update.mutate({ id: t.id, name: e.target.value })} />
            <input type="number" defaultValue={t.position} aria-label="Ordre" className={`${inputClass} h-9 w-20`} onBlur={(e) => Number(e.target.value) !== t.position && update.mutate({ id: t.id, position: Number(e.target.value) })} />
            {"is_active" in t && (
              <label className="flex items-center gap-1.5"><input type="checkbox" checked={t.is_active} onChange={() => update.mutate({ id: t.id, is_active: !t.is_active })} className="h-5 w-5" />Visible</label>
            )}
            <span className="text-encre-douce">{t.product_count} publié(s)</span>
            <Button size="sm" variant="ghost" className="ml-auto" onClick={() => window.confirm(`Supprimer « ${t.name} » ?`) && remove.mutate(t.id)}>Supprimer</Button>
          </li>
        ))}
      </ul>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nouveau nom" required minLength={2} aria-label="Nouveau nom" className={`${inputClass} h-10`} />
        <Button type="submit" size="sm" disabled={create.isPending}>Ajouter</Button>
      </form>
    </Card>
  );
}

export default function CollectionsPage() {
  return (
    <>
      <AdminTitle>Collections et familles</AdminTitle>
      <div className="grid gap-4 lg:grid-cols-2">
        <Taxons<Collection> kind="collections" title="Collections" />
        <Taxons<Family> kind="families" title="Familles olfactives" />
      </div>
    </>
  );
}
