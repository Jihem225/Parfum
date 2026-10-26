"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AdminTitle, Card } from "@/components/admin/ui";
import { Alert, Loading, StatusPill } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatDate, formatFCFA, formatPhone } from "@/lib/format";
import type { Customer, OrderSummary } from "@/lib/types";

export default function ClientPage() {
  const { id } = useParams<{ id: string }>();
  const { data: c, isLoading, error } = useQuery({ queryKey: ["customer", id], queryFn: () => api<Customer & { orders: OrderSummary[] }>(`/admin/customers/${id}`) });
  if (isLoading) return <Loading />;
  if (error || !c) return <Alert>{errorMessage(error)}</Alert>;
  return (
    <>
      <Link href="/admin/clients" className="text-sm underline underline-offset-4">← Clients</Link>
      <AdminTitle>{c.full_name}</AdminTitle>
      <Card>
        <div className="flex flex-wrap gap-6 text-sm">
          <span>{c.email}</span>
          <a href={`tel:${c.phone}`} className="font-semibold">{formatPhone(c.phone)}</a>
          <span>Inscrit le {formatDate(c.created_at)}</span>
          <span>{c.orders_count} commande(s) · {formatFCFA(c.delivered_total)} livrés</span>
        </div>
      </Card>
      <Card title="Commandes">
        <ul className="flex flex-col divide-y divide-filet text-sm">
          {c.orders.map((o) => (
            <li key={o.number}>
              <Link href={`/admin/commandes/${o.number}`} className="flex flex-wrap items-center gap-3 py-2">
                <strong>{o.number}</strong><StatusPill status={o.status} /><span className="text-encre-douce">{formatDate(o.created_at)}</span><span className="ml-auto">{formatFCFA(o.total)}</span>
              </Link>
            </li>
          ))}
          {c.orders.length === 0 && <li className="py-2 text-encre-douce">Aucune commande.</li>}
        </ul>
      </Card>
    </>
  );
}
