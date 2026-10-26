"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Button } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { formatFCFA, stockLabel } from "@/lib/format";
import { useCartMutations } from "@/lib/hooks";
import type { PublicVariant } from "@/lib/types";

const MAX = 5; // RG-22

/** Choix de contenance (US-03) : prix et disponibilité suivent la contenance choisie. */
export function AddToCart({ variants }: { variants: PublicVariant[] }) {
  const firstAvailable = variants.find((v) => v.stock_status !== "OUT") ?? variants[0];
  const [selected, setSelected] = useState(firstAvailable?.id);
  const [qty, setQty] = useState(1);
  const { add } = useCartMutations();
  const variant = variants.find((v) => v.id === selected);
  if (!variant) return null;
  const out = variant.stock_status === "OUT";
  const max = variant.stock_status === "LOW" ? Math.min(MAX, variant.low_stock_count ?? MAX) : MAX;

  return (
    <div className="flex flex-col gap-5">
      <div className="text-2xl font-bold tracking-[-0.01em]">{formatFCFA(variant.price)}</div>
      <fieldset className="flex flex-col gap-2.5">
        <legend className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-encre-douce">Contenance</legend>
        <div className="grid grid-cols-3 gap-2">
          {variants.map((v) => {
            const on = v.id === selected;
            return (
              <button
                key={v.id}
                type="button"
                aria-pressed={on}
                onClick={() => {
                  setSelected(v.id);
                  setQty(1);
                  add.reset();
                }}
                className={`flex h-16 flex-col items-center justify-center gap-0.5 border ${on ? "border-encre bg-encre text-porcelaine" : "border-[#cfc8be] bg-white"} ${v.stock_status === "OUT" ? "line-through decoration-1" : ""}`}
              >
                <span className="text-[15px] font-bold">{v.volume_ml} ml</span>
                <span className="text-xs">{formatFCFA(v.price)}</span>
              </button>
            );
          })}
        </div>
        <p className={`flex items-center gap-2 text-sm font-semibold ${out ? "text-erreur" : variant.stock_status === "LOW" ? "text-safran" : "text-succes"}`}>
          <span className="h-2 w-2 rounded-full bg-current" aria-hidden />
          {stockLabel(variant.stock_status, variant.low_stock_count)}
        </p>
      </fieldset>

      <div className="flex gap-2.5">
        <div className="flex h-[52px] items-center border border-[#cfc8be]">
          <button type="button" aria-label="Retirer un" disabled={qty <= 1} onClick={() => setQty(qty - 1)} className="h-full w-11 text-xl disabled:opacity-30">
            −
          </button>
          <span aria-live="polite" className="w-7 text-center font-bold">
            {qty}
          </span>
          <button type="button" aria-label="Ajouter un" disabled={qty >= max || out} onClick={() => setQty(qty + 1)} className="h-full w-11 text-xl disabled:opacity-30">
            +
          </button>
        </div>
        <Button
          className="flex-1"
          disabled={out || add.isPending}
          onClick={() => add.mutate({ variant_id: variant.id, quantity: qty })}
        >
          {out ? "Rupture de stock" : add.isPending ? "Ajout…" : "Ajouter au panier"}
        </Button>
      </div>
      {add.isSuccess && (
        <Alert tone="success">
          Ajouté au panier. <Link href="/panier" className="font-semibold underline">Voir le panier</Link>
        </Alert>
      )}
      {add.isError && <Alert>{errorMessage(add.error)}</Alert>}
    </div>
  );
}
