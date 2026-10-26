"use client";

import Link from "next/link";
import { Alert, Button, buttonClass, Loading } from "@/components/ui";
import { ProductImage } from "@/components/product-image";
import { errorMessage } from "@/lib/api";
import { formatFCFA } from "@/lib/format";
import { useCart, useCartMutations } from "@/lib/hooks";

export default function PanierPage() {
  const { data: cart, isLoading, error } = useCart();
  const { update, remove } = useCartMutations();
  const failure = update.error ?? remove.error;

  if (isLoading) return <Loading />;
  if (error || !cart) return <div className="p-6"><Alert>{errorMessage(error)}</Alert></div>;

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-6">
      <h1 className="mb-5 font-display text-[32px]">Panier</h1>
      {cart.items.length === 0 ? (
        <div className="flex flex-col items-start gap-4">
          <p>Votre panier est vide.</p>
          <Link href="/parfums" className={buttonClass()}>Découvrir les parfums</Link>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {failure && <Alert>{errorMessage(failure)}</Alert>}
          <ul className="flex flex-col divide-y divide-filet border-y border-filet">
            {cart.items.map((line) => (
              <li key={line.variant_id} className="flex gap-3 py-4">
                <Link href={`/parfums/${line.product_slug}`} className="w-20 flex-none" aria-hidden tabIndex={-1}>
                  <ProductImage image={line.image} productId={line.variant_id} name={line.product_name} className="aspect-[4/5]" />
                </Link>
                <div className="flex flex-1 flex-col gap-1">
                  <Link href={`/parfums/${line.product_slug}`} className="font-display text-[17px]">{line.product_name}</Link>
                  <span className="text-sm text-encre-douce">{line.volume_ml} ml · {formatFCFA(line.unit_price)}</span>
                  {line.issue === "UNAVAILABLE" && <span className="text-sm font-semibold text-erreur">Ce parfum n&apos;est plus disponible : retirez-le pour commander.</span>}
                  {line.issue === "INSUFFICIENT_STOCK" && (
                    <span className="text-sm font-semibold text-erreur">
                      {line.max_quantity ? `Plus que ${line.max_quantity} disponible(s) : réduisez la quantité.` : "En rupture de stock : retirez-le pour commander."}
                    </span>
                  )}
                  <div className="mt-1 flex items-center gap-3">
                    <label className="sr-only" htmlFor={`qty-${line.variant_id}`}>Quantité</label>
                    <select
                      id={`qty-${line.variant_id}`}
                      value={line.quantity}
                      disabled={update.isPending || line.issue === "UNAVAILABLE"}
                      onChange={(e) => update.mutate({ variant_id: line.variant_id, quantity: Number(e.target.value) })}
                      className="h-11 border border-[#cfc8be] bg-white px-2"
                    >
                      {Array.from({ length: Math.max(line.max_quantity, line.quantity, 1) }, (_, i) => i + 1).map((n) => (
                        <option key={n} value={n} disabled={n > Math.max(line.max_quantity, 1)}>{n}</option>
                      ))}
                    </select>
                    <Button variant="ghost" size="sm" onClick={() => remove.mutate(line.variant_id)} disabled={remove.isPending}>
                      Retirer
                    </Button>
                    <span className="ml-auto font-semibold">{formatFCFA(line.line_total)}</span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <div className="flex justify-between text-lg font-bold">
            <span>Sous-total</span>
            <span>{formatFCFA(cart.subtotal)}</span>
          </div>
          <p className="text-sm text-encre-douce">Frais de livraison selon votre commune, affichés à l&apos;étape suivante. Paiement en espèces à la livraison.</p>
          {cart.exceeds_cod_limit && (
            <Alert tone="info">
              Au-delà de 300 000 FCFA, <Link href="/contact" className="font-semibold underline">contactez la boutique</Link> pour passer votre commande.
            </Alert>
          )}
          {cart.can_checkout ? (
            <Link href="/commande" className={buttonClass()}>Commander</Link>
          ) : (
            <Button disabled>Commander</Button>
          )}
        </div>
      )}
    </div>
  );
}
