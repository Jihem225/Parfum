"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { OrderView } from "@/components/order-view";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { normalizePhone } from "@/lib/schemas";
import type { Order } from "@/lib/types";

export function TrackForm({ initialNumber }: { initialNumber: string }) {
  const [number, setNumber] = useState(initialNumber);
  const [phone, setPhone] = useState("");
  const track = useMutation({
    mutationFn: () => api<Order>("/orders/track", { json: { number: number.trim(), phone: normalizePhone(phone) } }),
  });
  return (
    <div className="flex flex-col gap-6">
      <form
        className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          track.mutate();
        }}
      >
        <Field label="Numéro de commande">
          <input value={number} onChange={(e) => setNumber(e.target.value)} required placeholder="PP-10001" className={inputClass} />
        </Field>
        <Field label="Téléphone">
          <input value={phone} onChange={(e) => setPhone(e.target.value)} required type="tel" inputMode="tel" placeholder="07 08 12 34 56" className={inputClass} />
        </Field>
        <Button type="submit" disabled={track.isPending}>{track.isPending ? "Recherche…" : "Suivre"}</Button>
      </form>
      {track.isError && <Alert>{errorMessage(track.error)}</Alert>}
      {track.data && <OrderView order={track.data} />}
    </div>
  );
}
