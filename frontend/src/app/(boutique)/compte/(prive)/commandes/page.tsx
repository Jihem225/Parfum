"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Alert, buttonClass, Loading, StatusPill } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDate, formatFCFA } from "@/lib/format";
import type { OrderSummary } from "@/lib/types";

export default function MesCommandesPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["my-orders"], queryFn: () => api<OrderSummary[]>("/me/orders") });
  if (isLoading) return <Loading />;
  if (error) return <Alert>{errorMessage(error)}</Alert>;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-[32px]">Mes commandes</h1>
      {!data?.length ? (
        <div className="flex flex-col items-start gap-3">
          <p>Aucune commande pour l&apos;instant.</p>
          <Link href="/parfums" className={buttonClass()}>Découvrir les parfums</Link>
        </div>
      ) : (
        <ul className="flex flex-col divide-y divide-filet border-y border-filet">
          {data.map((o) => (
            <li key={o.number}>
              <Link href={`/compte/commandes/${o.number}`} className="flex flex-wrap items-center gap-3 py-4 text-encre">
                <span className="font-bold">{o.number}</span>
                <StatusPill status={o.status} />
                <span className="text-sm text-encre-douce">{formatDate(o.created_at)} · {o.item_count} article{o.item_count > 1 ? "s" : ""}</span>
                <span className="ml-auto font-semibold">{formatFCFA(o.total)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
