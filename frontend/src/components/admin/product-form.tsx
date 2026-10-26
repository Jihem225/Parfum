"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { GENDER } from "@/lib/format";
import type { AdminProduct, Collection, Family, Gender } from "@/lib/types";

export type ProductFields = Pick<AdminProduct, "name" | "collection_id" | "family_id" | "gender" | "description" | "top_notes" | "heart_notes" | "base_notes">;

/** Fiche d'un parfum : création et modification. */
export function ProductForm({ initial, onSubmit, pending, submitLabel }: {
  initial?: ProductFields;
  onSubmit: (v: ProductFields) => void;
  pending: boolean;
  submitLabel: string;
}) {
  const collections = useQuery({ queryKey: ["admin-collections"], queryFn: () => api<Collection[]>("/admin/collections") });
  const families = useQuery({ queryKey: ["admin-families"], queryFn: () => api<Family[]>("/admin/families") });
  const [v, setV] = useState<ProductFields>(
    initial ?? { name: "", collection_id: 0, family_id: 0, gender: "MIXTE", description: "", top_notes: "", heart_notes: "", base_notes: "" },
  );
  const set = <K extends keyof ProductFields>(k: K, value: ProductFields[K]) => setV({ ...v, [k]: value });
  return (
    <form className="grid gap-4 md:grid-cols-2" onSubmit={(e) => { e.preventDefault(); onSubmit(v); }}>
      <Field label="Nom"><input value={v.name} onChange={(e) => set("name", e.target.value)} required minLength={2} maxLength={120} className={inputClass} /></Field>
      <Field label="Genre">
        <select value={v.gender} onChange={(e) => set("gender", e.target.value as Gender)} className={inputClass}>
          {Object.entries(GENDER).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </Field>
      <Field label="Collection">
        <select value={v.collection_id || ""} onChange={(e) => set("collection_id", Number(e.target.value))} required className={inputClass}>
          <option value="">Choisir</option>
          {collections.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </Field>
      <Field label="Famille olfactive">
        <select value={v.family_id || ""} onChange={(e) => set("family_id", Number(e.target.value))} required className={inputClass}>
          <option value="">Choisir</option>
          {families.data?.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
      </Field>
      <Field label="Notes de tête"><input value={v.top_notes} onChange={(e) => set("top_notes", e.target.value)} maxLength={255} className={inputClass} /></Field>
      <Field label="Notes de cœur"><input value={v.heart_notes} onChange={(e) => set("heart_notes", e.target.value)} maxLength={255} className={inputClass} /></Field>
      <Field label="Notes de fond"><input value={v.base_notes} onChange={(e) => set("base_notes", e.target.value)} maxLength={255} className={inputClass} /></Field>
      <div className="md:col-span-2">
        <Field label="Description"><textarea value={v.description} onChange={(e) => set("description", e.target.value)} rows={4} maxLength={5000} className={`${inputClass} h-auto py-2`} /></Field>
      </div>
      <Button type="submit" disabled={pending} className="md:col-span-2">{submitLabel}</Button>
    </form>
  );
}
