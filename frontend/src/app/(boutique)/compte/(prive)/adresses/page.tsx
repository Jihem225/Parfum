"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Alert, Button, Field, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatPhone } from "@/lib/format";
import { normalizePhone } from "@/lib/schemas";
import type { Address, Commune } from "@/lib/types";

const EMPTY = { label: "", recipient_name: "", phone: "", commune_id: "", address_line: "", landmark: "" };

export default function AdressesPage() {
  const qc = useQueryClient();
  const addresses = useQuery({ queryKey: ["addresses"], queryFn: () => api<Address[]>("/me/addresses") });
  const communes = useQuery({ queryKey: ["communes"], queryFn: () => api<Commune[]>("/delivery/communes") });
  const [form, setForm] = useState(EMPTY);
  const onSuccess = (list: Address[]) => qc.setQueryData(["addresses"], list);
  const add = useMutation({
    mutationFn: () =>
      api<Address[]>("/me/addresses", {
        json: { ...form, commune_id: Number(form.commune_id), phone: normalizePhone(form.phone) },
      }),
    onSuccess: (list) => {
      onSuccess(list);
      setForm(EMPTY);
    },
  });
  const makeDefault = useMutation({
    mutationFn: (id: number) => api<Address[]>(`/me/addresses/${id}`, { method: "PATCH", json: { is_default: true } }),
    onSuccess,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api<Address[]>(`/me/addresses/${id}`, { method: "DELETE" }),
    onSuccess,
  });
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  const failure = makeDefault.error ?? remove.error;

  if (addresses.isLoading) return <Loading />;
  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-display text-[32px]">Mes adresses</h1>
      {failure && <Alert>{errorMessage(failure)}</Alert>}
      <ul className="flex flex-col gap-3">
        {addresses.data?.map((a) => (
          <li key={a.id} className="flex flex-col gap-1 bg-surface p-4 text-sm">
            <div className="flex items-center gap-2">
              <strong>{a.label || "Adresse"}</strong>
              {a.is_default && <span className="rounded-full bg-encre px-2 py-0.5 text-xs text-porcelaine">Par défaut</span>}
            </div>
            <span>{a.recipient_name} · {formatPhone(a.phone)}</span>
            <span>{a.address_line}, {a.commune_name}</span>
            {a.landmark && <span className="text-encre-douce">Repère : {a.landmark}</span>}
            {!a.commune_served && <span className="font-semibold text-erreur">Commune plus desservie pour l&apos;instant.</span>}
            <div className="mt-1 flex gap-3">
              {!a.is_default && <Button variant="ghost" size="sm" onClick={() => makeDefault.mutate(a.id)}>Définir par défaut</Button>}
              <Button variant="ghost" size="sm" onClick={() => remove.mutate(a.id)}>Supprimer</Button>
            </div>
          </li>
        ))}
        {addresses.data?.length === 0 && <p className="text-encre-douce">Aucune adresse enregistrée.</p>}
      </ul>
      <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <h2 className="font-display text-[22px]">Ajouter une adresse</h2>
        <Field label="Nom de l'adresse (facultatif)"><input value={form.label} onChange={set("label")} placeholder="Maison, Bureau…" className={inputClass} /></Field>
        <Field label="Destinataire"><input value={form.recipient_name} onChange={set("recipient_name")} required minLength={2} className={inputClass} /></Field>
        <Field label="Téléphone"><input value={form.phone} onChange={set("phone")} type="tel" required className={inputClass} /></Field>
        <Field label="Commune">
          <select value={form.commune_id} onChange={set("commune_id")} required className={inputClass}>
            <option value="">Choisissez</option>
            {communes.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <Field label="Adresse"><input value={form.address_line} onChange={set("address_line")} required minLength={3} className={inputClass} /></Field>
        <Field label="Point de repère (facultatif)"><input value={form.landmark} onChange={set("landmark")} className={inputClass} /></Field>
        {add.isError && <Alert>{errorMessage(add.error)}</Alert>}
        <Button type="submit" disabled={add.isPending}>Ajouter</Button>
      </form>
    </div>
  );
}
