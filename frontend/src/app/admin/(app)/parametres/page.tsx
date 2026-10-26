"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { OwnerOnly } from "@/components/admin/owner-only";
import { AdminTitle, Card, Table, td } from "@/components/admin/ui";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { normalizePhone } from "@/lib/schemas";
import type { Commune, ShopInfo } from "@/lib/types";

function ShopForm({ shop }: { shop: ShopInfo }) {
  const qc = useQueryClient();
  const [v, setV] = useState({ ...shop, phone: shop.phone ?? "", whatsapp: shop.whatsapp ?? "", email: shop.email ?? "" });
  const save = useMutation({
    mutationFn: () =>
      api<ShopInfo>("/admin/settings/shop", {
        method: "PUT",
        json: { ...v, phone: v.phone ? normalizePhone(v.phone) : null, whatsapp: v.whatsapp ? normalizePhone(v.whatsapp) : null, email: v.email || null },
      }),
    onSuccess: (s) => qc.setQueryData(["shop"], s),
  });
  const f = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  return (
    <Card title="Informations de la boutique">
      <form className="grid gap-3 md:grid-cols-2" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Field label="Nom"><input value={v.name} onChange={f("name")} required minLength={2} className={inputClass} /></Field>
        <Field label="E-mail"><input type="email" value={v.email} onChange={f("email")} className={inputClass} /></Field>
        <Field label="Téléphone"><input type="tel" value={v.phone} onChange={f("phone")} className={inputClass} /></Field>
        <Field label="WhatsApp"><input type="tel" value={v.whatsapp} onChange={f("whatsapp")} className={inputClass} /></Field>
        <Field label="Adresse"><input value={v.address} onChange={f("address")} maxLength={255} className={inputClass} /></Field>
        <Field label="Horaires"><input value={v.opening_hours} onChange={f("opening_hours")} maxLength={120} className={inputClass} /></Field>
        {save.isError && <Alert>{errorMessage(save.error)}</Alert>}
        {save.isSuccess && <Alert tone="success">Informations enregistrées.</Alert>}
        <Button type="submit" disabled={save.isPending} className="md:col-span-2">Enregistrer</Button>
      </form>
    </Card>
  );
}

function Communes() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["admin-communes"], queryFn: () => api<Commune[]>("/admin/communes") });
  const [form, setForm] = useState({ name: "", delivery_fee: "", delay_label: "24 h" });
  const refresh = () => qc.invalidateQueries({ queryKey: ["admin-communes"] });
  const create = useMutation({
    mutationFn: () => api("/admin/communes", { json: { ...form, delivery_fee: Number(form.delivery_fee) } }),
    onSuccess: () => { setForm({ name: "", delivery_fee: "", delay_label: "24 h" }); refresh(); },
  });
  const update = useMutation({ mutationFn: ({ id, ...v }: { id: number } & Partial<Commune>) => api(`/admin/communes/${id}`, { method: "PATCH", json: v }), onSuccess: refresh });
  const failure = create.error ?? update.error;
  return (
    <Card title="Communes desservies">
      <p className="text-sm text-encre-douce">Un changement de frais ne modifie pas les commandes déjà passées.</p>
      {failure && <Alert>{errorMessage(failure)}</Alert>}
      <Table head={["Commune", "Frais (FCFA)", "Délai", "Ordre", "Desservie"]}>
        {list.data?.map((c) => (
          <tr key={c.id}>
            <td className={td}><input defaultValue={c.name} aria-label="Nom" className={`${inputClass} h-9`} onBlur={(e) => e.target.value !== c.name && update.mutate({ id: c.id, name: e.target.value })} /></td>
            <td className={td}><input type="number" min={0} defaultValue={c.delivery_fee} aria-label="Frais" className={`${inputClass} h-9 w-28`} onBlur={(e) => Number(e.target.value) !== c.delivery_fee && update.mutate({ id: c.id, delivery_fee: Number(e.target.value) })} /></td>
            <td className={td}><input defaultValue={c.delay_label} aria-label="Délai" className={`${inputClass} h-9 w-24`} onBlur={(e) => e.target.value !== c.delay_label && update.mutate({ id: c.id, delay_label: e.target.value })} /></td>
            <td className={td}><input type="number" defaultValue={c.position} aria-label="Ordre" className={`${inputClass} h-9 w-20`} onBlur={(e) => Number(e.target.value) !== c.position && update.mutate({ id: c.id, position: Number(e.target.value) })} /></td>
            <td className={td}><input type="checkbox" checked={c.is_active} onChange={() => update.mutate({ id: c.id, is_active: !c.is_active })} aria-label="Desservie" className="h-5 w-5" /></td>
          </tr>
        ))}
      </Table>
      <form className="grid grid-cols-2 gap-3 md:grid-cols-4 md:items-end" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <Field label="Commune"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required minLength={2} className={inputClass} /></Field>
        <Field label="Frais (FCFA)"><input type="number" min={0} value={form.delivery_fee} onChange={(e) => setForm({ ...form, delivery_fee: e.target.value })} required className={inputClass} /></Field>
        <Field label="Délai"><input value={form.delay_label} onChange={(e) => setForm({ ...form, delay_label: e.target.value })} required className={inputClass} /></Field>
        <Button type="submit" disabled={create.isPending}>Ajouter</Button>
      </form>
    </Card>
  );
}

export default function ParametresPage() {
  const shop = useQuery({ queryKey: ["shop"], queryFn: () => api<ShopInfo>("/shop") });
  return (
    <OwnerOnly>
      <AdminTitle>Boutique et livraison</AdminTitle>
      {shop.data && <ShopForm shop={shop.data} />}
      <Communes />
    </OwnerOnly>
  );
}
