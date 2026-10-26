"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ProductForm } from "@/components/admin/product-form";
import { AdminTitle, Card, Table, td } from "@/components/admin/ui";
import { ProductImage } from "@/components/product-image";
import { Alert, Button, Field, inputClass, Loading } from "@/components/ui";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatFCFA, PRODUCT_STATUS } from "@/lib/format";
import type { AdminProduct, AdminVariant, Image } from "@/lib/types";

export default function ProduitPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const key = ["admin-product", id];
  const product = useQuery({ queryKey: key, queryFn: () => api<AdminProduct>(`/admin/products/${id}`) });
  const set = (p: AdminProduct) => {
    qc.setQueryData(key, p);
    qc.invalidateQueries({ queryKey: ["admin-products"] });
  };
  const refresh = () => qc.invalidateQueries({ queryKey: key });
  const save = useMutation({ mutationFn: (v: object) => api<AdminProduct>(`/admin/products/${id}`, { method: "PATCH", json: v }), onSuccess: set });
  const status = useMutation({ mutationFn: (action: "publish" | "unpublish" | "archive") => api<AdminProduct>(`/admin/products/${id}/${action}`, { method: "POST" }), onSuccess: set });
  const remove = useMutation({
    mutationFn: () => api(`/admin/products/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-products"] });
      router.push("/admin/produits");
    },
  });

  if (product.isLoading) return <Loading />;
  if (product.error || !product.data) return <Alert>{errorMessage(product.error)}</Alert>;
  const p = product.data;
  const statusError = status.error ?? remove.error;
  return (
    <>
      <Link href="/admin/produits" className="text-sm underline underline-offset-4">← Produits</Link>
      <AdminTitle
        actions={
          <div className="flex flex-wrap gap-2">
            {p.status !== "PUBLISHED" && <Button size="sm" onClick={() => status.mutate("publish")} disabled={status.isPending}>Publier</Button>}
            {p.status !== "DRAFT" && <Button size="sm" variant="secondary" onClick={() => status.mutate("unpublish")} disabled={status.isPending}>{p.status === "ARCHIVED" ? "Restaurer en brouillon" : "Dépublier"}</Button>}
            {p.status !== "ARCHIVED" && <Button size="sm" variant="secondary" onClick={() => status.mutate("archive")} disabled={status.isPending}>Archiver</Button>}
            <Button size="sm" variant="danger" disabled={remove.isPending} onClick={() => window.confirm(`Supprimer définitivement « ${p.name} » ?`) && remove.mutate()}>Supprimer</Button>
          </div>
        }
      >
        {p.name} <span className="align-middle text-base font-normal text-encre-douce">· {PRODUCT_STATUS[p.status]}</span>
      </AdminTitle>
      {p.status === "PUBLISHED" && <Link href={`/parfums/${p.slug}`} target="_blank" className="text-sm underline underline-offset-4">Voir sur la boutique</Link>}
      {statusError && (
        <Alert>
          {errorMessage(statusError)}
          {statusError instanceof ApiError && Array.isArray(statusError.details) && (
            <ul className="mt-1 list-disc pl-5">{(statusError.details as string[]).map((d) => <li key={d}>{d}</li>)}</ul>
          )}
        </Alert>
      )}
      <Card title="Fiche">
        {save.isError && <Alert>{errorMessage(save.error)}</Alert>}
        {save.isSuccess && <Alert tone="success">Fiche enregistrée.</Alert>}
        <ProductForm key={p.id} initial={p} onSubmit={(v) => save.mutate(v)} pending={save.isPending} submitLabel="Enregistrer la fiche" />
      </Card>
      <Variants product={p} onChange={set} onDeleted={refresh} />
      <Images product={p} onChange={refresh} />
    </>
  );
}

function Variants({ product, onChange, onDeleted }: { product: AdminProduct; onChange: (p: AdminProduct) => void; onDeleted: () => void }) {
  const [form, setForm] = useState({ volume_ml: "", sku: "", price: "", low_stock_threshold: "5", initial_stock: "0" });
  const add = useMutation({
    mutationFn: () =>
      api<AdminProduct>(`/admin/products/${product.id}/variants`, {
        json: { volume_ml: Number(form.volume_ml), sku: form.sku, price: Number(form.price), low_stock_threshold: Number(form.low_stock_threshold), initial_stock: Number(form.initial_stock) },
      }),
    onSuccess: (p) => {
      onChange(p);
      setForm({ volume_ml: "", sku: "", price: "", low_stock_threshold: "5", initial_stock: "0" });
    },
  });
  const update = useMutation({
    mutationFn: ({ id, ...v }: Partial<AdminVariant> & { id: number }) => api<AdminProduct>(`/admin/variants/${id}`, { method: "PATCH", json: v }),
    onSuccess: onChange,
  });
  const remove = useMutation({ mutationFn: (id: number) => api(`/admin/variants/${id}`, { method: "DELETE" }), onSuccess: onDeleted });
  const failure = add.error ?? update.error ?? remove.error;
  const f = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  return (
    <Card title="Contenances">
      <p className="text-sm text-encre-douce">Chaque changement de prix est inscrit au journal. Le stock se gère dans « Stock ».</p>
      {failure && <Alert>{errorMessage(failure)}</Alert>}
      <Table head={["Contenance", "SKU", "Prix (FCFA)", "Seuil d'alerte", "Physique / réservé", "Active", ""]}>
        {product.variants.map((v) => (
          <tr key={v.id}>
            <td className={td}>{v.volume_ml} ml</td>
            <td className={`${td} font-mono`}>{v.sku}</td>
            <td className={td}>
              <input type="number" defaultValue={v.price} min={1} aria-label={`Prix ${v.volume_ml} ml`} className={`${inputClass} h-9 w-28`}
                onBlur={(e) => Number(e.target.value) !== v.price && update.mutate({ id: v.id, price: Number(e.target.value) })} />
            </td>
            <td className={td}>
              <input type="number" defaultValue={v.low_stock_threshold} min={0} aria-label={`Seuil ${v.volume_ml} ml`} className={`${inputClass} h-9 w-20`}
                onBlur={(e) => Number(e.target.value) !== v.low_stock_threshold && update.mutate({ id: v.id, low_stock_threshold: Number(e.target.value) })} />
            </td>
            <td className={td}>{v.stock_physical} / {v.stock_reserved}</td>
            <td className={td}><input type="checkbox" checked={v.is_active} onChange={() => update.mutate({ id: v.id, is_active: !v.is_active })} aria-label={`Active ${v.volume_ml} ml`} className="h-5 w-5" /></td>
            <td className={td}><Button size="sm" variant="ghost" onClick={() => window.confirm("Supprimer cette contenance ?") && remove.mutate(v.id)}>Supprimer</Button></td>
          </tr>
        ))}
      </Table>
      <form className="grid grid-cols-2 gap-3 md:grid-cols-6 md:items-end" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field label="Volume (ml)"><input type="number" min={1} value={form.volume_ml} onChange={f("volume_ml")} required className={inputClass} /></Field>
        <Field label="SKU"><input value={form.sku} onChange={f("sku")} required pattern="[A-Za-z0-9][A-Za-z0-9\-]{1,39}" className={inputClass} /></Field>
        <Field label="Prix (FCFA)"><input type="number" min={1} value={form.price} onChange={f("price")} required className={inputClass} /></Field>
        <Field label="Seuil"><input type="number" min={0} value={form.low_stock_threshold} onChange={f("low_stock_threshold")} className={inputClass} /></Field>
        <Field label="Stock initial"><input type="number" min={0} value={form.initial_stock} onChange={f("initial_stock")} className={inputClass} /></Field>
        <Button type="submit" disabled={add.isPending}>Ajouter</Button>
      </form>
      {product.variants.length > 0 && <p className="text-xs text-encre-douce">Prix les plus bas : {formatFCFA(Math.min(...product.variants.map((v) => v.price)))}.</p>}
    </Card>
  );
}

function Images({ product, onChange }: { product: AdminProduct; onChange: () => void }) {
  const [alt, setAlt] = useState("");
  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      form.append("alt_text", alt || product.name);
      return api<Image>(`/admin/products/${product.id}/images`, { form });
    },
    onSuccess: () => {
      setAlt("");
      onChange();
    },
  });
  const reorder = useMutation({
    mutationFn: (ids: number[]) => api(`/admin/products/${product.id}/images/order`, { method: "PUT", json: { image_ids: ids } }),
    onSuccess: onChange,
  });
  const remove = useMutation({ mutationFn: (imageId: number) => api(`/admin/products/${product.id}/images/${imageId}`, { method: "DELETE" }), onSuccess: onChange });
  const ids = product.images.map((i) => i.id);
  const move = (index: number, delta: number) => {
    const next = [...ids];
    const [moved] = next.splice(index, 1);
    if (moved === undefined) return;
    next.splice(index + delta, 0, moved);
    reorder.mutate(next);
  };
  const failure = upload.error ?? reorder.error ?? remove.error;
  return (
    <Card title="Images">
      <p className="text-sm text-encre-douce">JPG, PNG ou WebP, 5 Mo maximum. La première image est l&apos;image principale.</p>
      {failure && <Alert>{errorMessage(failure)}</Alert>}
      <div className="flex flex-wrap gap-3">
        {product.images.map((img, i) => (
          <div key={img.id} className="flex w-32 flex-col gap-1 text-xs">
            <ProductImage image={img} productId={product.id} name={product.name} className="aspect-[4/5]" />
            <span className="truncate" title={img.alt_text}>{img.alt_text}</span>
            <div className="flex justify-between">
              <button type="button" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Avancer" className="px-2 py-1 disabled:opacity-30">←</button>
              <button type="button" onClick={() => window.confirm("Supprimer cette image ?") && remove.mutate(img.id)} className="px-2 py-1 underline">Supprimer</button>
              <button type="button" disabled={i === ids.length - 1} onClick={() => move(i, 1)} aria-label="Reculer" className="px-2 py-1 disabled:opacity-30">→</button>
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-2 md:items-end">
        <Field label="Texte alternatif (description pour l'accessibilité)"><input value={alt} onChange={(e) => setAlt(e.target.value)} maxLength={255} className={inputClass} /></Field>
        <Field label={upload.isPending ? "Envoi en cours…" : "Ajouter une image"}>
          <input type="file" accept="image/jpeg,image/png,image/webp" disabled={upload.isPending}
            onChange={(e) => { const file = e.target.files?.[0]; if (file) upload.mutate(file); e.target.value = ""; }}
            className="text-sm" />
        </Field>
      </div>
    </Card>
  );
}
