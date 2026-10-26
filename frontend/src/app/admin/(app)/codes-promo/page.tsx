"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AdminTitle, Card } from "@/components/admin/ui";
import { Alert, Button, Field, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime, formatFCFA } from "@/lib/format";
import { useMe } from "@/lib/hooks";
import type { PromoCode, PromoKind } from "@/lib/types";

type Draft = {
  code: string;
  kind: PromoKind;
  value: string;
  max_discount: string;
  min_subtotal: string;
  starts_at: string; // datetime-local, heure d'Abidjan (UTC)
  ends_at: string;
  max_uses: string;
  is_active: boolean;
  note: string;
};

const EMPTY: Draft = { code: "", kind: "PERCENT", value: "", max_discount: "", min_subtotal: "", starts_at: "", ends_at: "", max_uses: "", is_active: true, note: "" };

// Abidjan est en UTC toute l'année : la saisie « heure locale » de la boutique est de l'UTC.
const toInput = (iso: string | null) => (iso ? new Date(iso).toISOString().slice(0, 16) : "");
const toIso = (local: string) => (local ? `${local}:00Z` : null);
const num = (v: string) => (v.trim() ? Number(v) : null);

function draftOf(p: PromoCode): Draft {
  const text = (n: number | null) => (n === null ? "" : String(n));
  return {
    code: p.code,
    kind: p.kind,
    value: String(p.value),
    max_discount: text(p.max_discount),
    min_subtotal: text(p.min_subtotal),
    starts_at: toInput(p.starts_at),
    ends_at: toInput(p.ends_at),
    max_uses: text(p.max_uses),
    is_active: p.is_active,
    note: p.note,
  };
}

function payload(d: Draft) {
  return {
    kind: d.kind,
    value: Number(d.value),
    max_discount: d.kind === "PERCENT" ? num(d.max_discount) : null,
    min_subtotal: num(d.min_subtotal),
    starts_at: toIso(d.starts_at),
    ends_at: toIso(d.ends_at),
    max_uses: num(d.max_uses),
    is_active: d.is_active,
    note: d.note,
  };
}

function describe(p: PromoCode): string {
  const reduction = p.kind === "PERCENT" ? `${p.value} %${p.max_discount ? ` (max ${formatFCFA(p.max_discount)})` : ""}` : formatFCFA(p.value);
  const rules = [
    p.min_subtotal && `dès ${formatFCFA(p.min_subtotal)} d'articles`,
    p.starts_at && `à partir du ${formatDateTime(p.starts_at)}`,
    p.ends_at && `jusqu'au ${formatDateTime(p.ends_at)}`,
    p.max_uses && `${p.max_uses} utilisations au total`,
    "1 fois par téléphone",
  ].filter(Boolean);
  return `${reduction} sur les articles · ${rules.join(" · ")}`;
}

/** Codes promo (étape 13) : l'équipe consulte, le Propriétaire crée et modifie. */
export default function CodesPromoPage() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const owner = me?.role === "OWNER";
  const list = useQuery({ queryKey: ["promo-codes"], queryFn: () => api<PromoCode[]>("/admin/promo-codes") });
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [editing, setEditing] = useState<number | null>(null);
  const done = () => {
    qc.invalidateQueries({ queryKey: ["promo-codes"] });
    setDraft(EMPTY);
    setEditing(null);
  };
  const save = useMutation({
    mutationFn: () =>
      editing === null
        ? api<PromoCode>("/admin/promo-codes", { json: { code: draft.code, ...payload(draft) } })
        : api<PromoCode>(`/admin/promo-codes/${editing}`, { method: "PUT", json: payload(draft) }),
    onSuccess: done,
  });
  const toggle = useMutation({
    mutationFn: (p: PromoCode) => api(`/admin/promo-codes/${p.id}`, { method: "PUT", json: payload({ ...draftOf(p), is_active: !p.is_active }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promo-codes"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api(`/admin/promo-codes/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promo-codes"] }),
  });
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setDraft({ ...draft, [k]: v });
  const failure = list.error ?? toggle.error ?? remove.error;

  return (
    <>
      <AdminTitle>Codes promo</AdminTitle>
      <p className="text-sm text-encre-douce">
        Réduction sur les articles (pas sur la livraison), un code par commande, une fois par numéro de téléphone. Une commande annulée rend
        le code. Heures en heure d&apos;Abidjan.
      </p>
      {failure && <Alert>{errorMessage(failure)}</Alert>}
      {list.isLoading && <Loading />}
      <ul className="flex flex-col gap-3">
        {list.data?.map((p) => (
          <li key={p.id} className="flex flex-col gap-2 rounded border border-filet bg-white p-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <strong className="font-mono text-base tracking-wide">{p.code}</strong>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${p.is_active ? "bg-succes text-white" : "bg-[#e2ddd5] text-encre"}`}>{p.is_active ? "Actif" : "Désactivé"}</span>
              <span className="text-encre-douce">{p.uses} utilisation(s) · {formatFCFA(p.discount_total)} de remises</span>
              {owner && (
                <div className="ml-auto flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => { setEditing(p.id); setDraft(draftOf(p)); }}>Modifier</Button>
                  <Button size="sm" variant="secondary" disabled={toggle.isPending} onClick={() => toggle.mutate(p)}>{p.is_active ? "Désactiver" : "Activer"}</Button>
                  {p.uses === 0 && <Button size="sm" variant="ghost" onClick={() => window.confirm(`Supprimer le code ${p.code} ?`) && remove.mutate(p.id)}>Supprimer</Button>}
                </div>
              )}
            </div>
            <span>{describe(p)}</span>
            {p.note && <span className="text-encre-douce">{p.note}</span>}
          </li>
        ))}
        {list.data?.length === 0 && <li className="text-encre-douce">Aucun code promo.</li>}
      </ul>

      {owner && (
        <Card title={editing === null ? "Nouveau code" : `Modifier ${draft.code}`}>
          <form
            className="grid gap-4 md:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            <Field label="Code" hint="Lettres, chiffres et tirets ; non modifiable ensuite.">
              <input value={draft.code} onChange={(e) => set("code", e.target.value.toUpperCase())} disabled={editing !== null} required minLength={3} maxLength={30} className={`${inputClass} font-mono uppercase`} />
            </Field>
            <Field label="Réduction">
              <div className="flex gap-2">
                <select value={draft.kind} onChange={(e) => set("kind", e.target.value as PromoKind)} className={`${inputClass} w-36`} aria-label="Type de réduction">
                  <option value="PERCENT">Pourcentage</option>
                  <option value="FIXED">Montant FCFA</option>
                </select>
                <input type="number" min={1} max={draft.kind === "PERCENT" ? 90 : undefined} value={draft.value} onChange={(e) => set("value", e.target.value)} required aria-label={draft.kind === "PERCENT" ? "Pourcentage" : "Montant"} className={inputClass} />
              </div>
            </Field>
            {draft.kind === "PERCENT" && (
              <Field label="Plafond de la réduction (FCFA, facultatif)">
                <input type="number" min={1} value={draft.max_discount} onChange={(e) => set("max_discount", e.target.value)} className={inputClass} />
              </Field>
            )}
            <Field label="Montant d'articles minimum (FCFA, facultatif)">
              <input type="number" min={1} value={draft.min_subtotal} onChange={(e) => set("min_subtotal", e.target.value)} className={inputClass} />
            </Field>
            <Field label="Début (facultatif)">
              <input type="datetime-local" value={draft.starts_at} onChange={(e) => set("starts_at", e.target.value)} className={inputClass} />
            </Field>
            <Field label="Fin (facultatif)">
              <input type="datetime-local" value={draft.ends_at} onChange={(e) => set("ends_at", e.target.value)} className={inputClass} />
            </Field>
            <Field label="Utilisations au total (facultatif)" hint="En plus de la limite d'une fois par téléphone.">
              <input type="number" min={1} value={draft.max_uses} onChange={(e) => set("max_uses", e.target.value)} className={inputClass} />
            </Field>
            <Field label="Note interne (facultatif)" hint="Campagne, partenaire…">
              <input value={draft.note} onChange={(e) => set("note", e.target.value)} maxLength={200} className={inputClass} />
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={draft.is_active} onChange={(e) => set("is_active", e.target.checked)} className="h-5 w-5" />
              Actif
            </label>
            {save.isError && <div className="md:col-span-2"><Alert>{errorMessage(save.error)}</Alert></div>}
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit" disabled={save.isPending}>{editing === null ? "Créer le code" : "Enregistrer"}</Button>
              {editing !== null && <Button variant="ghost" onClick={() => { setEditing(null); setDraft(EMPTY); }}>Annuler</Button>}
            </div>
          </form>
        </Card>
      )}
    </>
  );
}
