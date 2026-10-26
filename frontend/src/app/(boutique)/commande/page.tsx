"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { useForm, useWatch } from "react-hook-form";
import type { z } from "zod";
import { Alert, Button, buttonClass, Field, inputClass, Loading } from "@/components/ui";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatFCFA } from "@/lib/format";
import { useCart, useMe } from "@/lib/hooks";
import { checkoutSchema, type CheckoutValues } from "@/lib/schemas";
import type { Address, CheckoutPreview, Commune, Order } from "@/lib/types";

type Out = z.output<typeof checkoutSchema>;

export default function CommandePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const cart = useCart();
  const communes = useQuery({ queryKey: ["communes"], queryFn: () => api<Commune[]>("/delivery/communes") });
  const addresses = useQuery({
    queryKey: ["addresses"],
    queryFn: () => api<Address[]>("/me/addresses"),
    enabled: me?.role === "CUSTOMER",
  });
  // Une clé par visite de la page, créée au premier envoi : un double clic ou un nouvel essai
  // après une coupure réseau renvoie la même commande (pas de doublon).
  const idempotencyKey = useRef<string | null>(null);
  const form = useForm<CheckoutValues, unknown, Out>({
    resolver: zodResolver(checkoutSchema),
    defaultValues: { customer_name: "", phone: "", email: "", commune_id: "", address_line: "", landmark: "", accept_terms: false },
  });
  const { register, handleSubmit, setValue, setError, control, formState: { errors } } = form;

  // Préremplissage pour un client connecté : profil puis adresse par défaut.
  const defaultAddress = addresses.data?.find((a) => a.is_default && a.commune_served);
  useEffect(() => {
    if (!me || me.role !== "CUSTOMER") return;
    setValue("customer_name", me.full_name);
    setValue("phone", me.phone);
    setValue("email", me.email);
  }, [me, setValue]);
  useEffect(() => {
    if (!defaultAddress) return;
    setValue("customer_name", defaultAddress.recipient_name);
    setValue("phone", defaultAddress.phone);
    setValue("commune_id", String(defaultAddress.commune_id));
    setValue("address_line", defaultAddress.address_line);
    setValue("landmark", defaultAddress.landmark ?? "");
  }, [defaultAddress, setValue]);

  const communeId = Number(useWatch({ control, name: "commune_id" })) || 0;
  const preview = useQuery({
    queryKey: ["preview", communeId, cart.data?.subtotal, cart.data?.item_count],
    queryFn: () => api<CheckoutPreview>("/checkout/preview", { json: { commune_id: communeId } }),
    enabled: communeId > 0,
  });

  const place = useMutation({
    mutationFn: (v: Out) => {
      idempotencyKey.current ??= crypto.randomUUID();
      return api<Order>("/orders", {
        json: { ...v, email: v.email || null, expected_total: preview.data?.total, idempotency_key: idempotencyKey.current },
      });
    },
    onSuccess: (order) => {
      qc.invalidateQueries({ queryKey: ["cart"] });
      router.push(`/commande/confirmee?numero=${order.number}`);
    },
    onError: (e) => {
      if (!(e instanceof ApiError)) return;
      for (const [field, message] of Object.entries(e.fieldErrors())) setError(field as keyof CheckoutValues, { message });
      if (["PRICE_CHANGED", "CART_CHANGED", "INSUFFICIENT_STOCK"].includes(e.code)) {
        qc.invalidateQueries({ queryKey: ["cart"] });
        qc.invalidateQueries({ queryKey: ["preview"] });
      }
    },
  });

  if (cart.isLoading) return <Loading />;
  if (!cart.data?.items.length && !place.isSuccess) {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-start gap-4 px-4 py-8">
        <h1 className="font-display text-[32px]">Commande</h1>
        <p>Votre panier est vide.</p>
        <Link href="/parfums" className={buttonClass()}>Découvrir les parfums</Link>
      </div>
    );
  }

  const p = preview.data;
  return (
    <form onSubmit={handleSubmit((v) => place.mutate(v))} noValidate className="mx-auto grid w-full max-w-5xl gap-8 px-4 py-6 md:grid-cols-[1fr_360px]">
      <div className="flex flex-col gap-4">
        <h1 className="font-display text-[32px]">Commande</h1>
        {!me && (
          <p className="text-sm text-encre-douce">
            Pas besoin de compte. <Link href="/compte/connexion?suite=/commande" className="font-semibold underline">Se connecter</Link> pour retrouver vos adresses.
          </p>
        )}
        {(addresses.data?.length ?? 0) > 1 && (
          <Field label="Mes adresses">
            <select
              className={inputClass}
              defaultValue=""
              onChange={(e) => {
                const a = addresses.data?.find((x) => x.id === Number(e.target.value));
                if (!a) return;
                setValue("customer_name", a.recipient_name);
                setValue("phone", a.phone);
                setValue("commune_id", String(a.commune_id));
                setValue("address_line", a.address_line);
                setValue("landmark", a.landmark ?? "");
              }}
            >
              <option value="">Choisir une adresse enregistrée</option>
              {addresses.data?.filter((a) => a.commune_served).map((a) => (
                <option key={a.id} value={a.id}>{a.label || a.address_line} — {a.commune_name}</option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Nom et prénom" error={errors.customer_name?.message}>
          <input {...register("customer_name")} autoComplete="name" className={inputClass} aria-invalid={!!errors.customer_name} />
        </Field>
        <Field label="Téléphone" hint="Nous vous appelons pour confirmer la commande." error={errors.phone?.message}>
          <input {...register("phone")} type="tel" inputMode="tel" autoComplete="tel" placeholder="07 08 12 34 56" className={inputClass} aria-invalid={!!errors.phone} />
        </Field>
        <Field label="E-mail (facultatif)" hint="Pour recevoir le suivi de votre commande." error={errors.email?.message}>
          <input {...register("email")} type="email" autoComplete="email" className={inputClass} aria-invalid={!!errors.email} />
        </Field>
        <Field label="Commune" error={errors.commune_id?.message}>
          <select {...register("commune_id")} className={inputClass} aria-invalid={!!errors.commune_id}>
            <option value="">Choisissez votre commune</option>
            {communes.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} — {formatFCFA(c.delivery_fee)}, {c.delay_label}
              </option>
            ))}
          </select>
        </Field>
        {communes.data?.length === 0 && <Alert tone="info">Les livraisons ne sont pas encore ouvertes. Revenez bientôt.</Alert>}
        <Field label="Adresse" hint="Quartier, rue, bâtiment, étage." error={errors.address_line?.message}>
          <input {...register("address_line")} autoComplete="street-address" className={inputClass} aria-invalid={!!errors.address_line} />
        </Field>
        <Field label="Point de repère (facultatif)" error={errors.landmark?.message}>
          <input {...register("landmark")} placeholder="Près de la pharmacie…" className={inputClass} />
        </Field>
        <label className="flex items-start gap-3 text-sm">
          <input type="checkbox" {...register("accept_terms")} className="mt-0.5 h-5 w-5 flex-none" aria-invalid={!!errors.accept_terms} />
          <span>
            J&apos;accepte les <Link href="/infos/cgv" target="_blank" className="font-semibold underline">conditions générales de vente</Link>.
          </span>
        </label>
        {errors.accept_terms && <span role="alert" className="text-sm text-erreur">{errors.accept_terms.message}</span>}
      </div>

      <aside className="flex h-fit flex-col gap-3 bg-surface p-5 md:sticky md:top-20">
        <h2 className="font-display text-[22px]">Récapitulatif</h2>
        {cart.data?.items.map((l) => (
          <div key={l.variant_id} className="flex justify-between gap-3 text-sm">
            <span>{l.product_name} · {l.volume_ml} ml × {l.quantity}</span>
            <span>{formatFCFA(l.line_total)}</span>
          </div>
        ))}
        <div className="flex justify-between border-t border-filet pt-2 text-sm">
          <span>Livraison</span>
          <span>{p ? `${formatFCFA(p.delivery_fee)} · ${p.delivery_delay_label}` : "selon la commune"}</span>
        </div>
        <div className="flex justify-between text-lg font-bold">
          <span>Total</span>
          <span>{formatFCFA(p ? p.total : (cart.data?.subtotal ?? 0))}</span>
        </div>
        <p className="text-sm">À payer <strong>en espèces à la livraison</strong>.</p>
        {p?.exceeds_cod_limit && <Alert tone="info">Au-delà de 300 000 FCFA, contactez la boutique pour commander.</Alert>}
        {place.isError && (
          <Alert>
            {errorMessage(place.error)}
            {place.error instanceof ApiError && place.error.code === "CART_CHANGED" && (
              <> <Link href="/panier" className="font-semibold underline">Vérifier le panier</Link></>
            )}
          </Alert>
        )}
        <Button type="submit" disabled={place.isPending || !p?.can_order}>
          {place.isPending ? "Validation…" : "Valider la commande"}
        </Button>
        {!communeId && <p className="text-xs text-encre-douce">Choisissez votre commune pour voir le total.</p>}
      </aside>
    </form>
  );
}
