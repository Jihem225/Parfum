"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { AdminTitle, Card } from "@/components/admin/ui";
import { Alert, inputClass, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatFCFA, ORDER_STATUS } from "@/lib/format";
import type { Dashboard, OrderStatus } from "@/lib/types";

function Kpi({ label, value, href }: { label: string; value: string; href?: string }) {
  const body = (
    <>
      <span className="text-xs font-semibold uppercase tracking-wide text-encre-douce">{label}</span>
      <span className="text-2xl font-bold">{value}</span>
    </>
  );
  const cls = "flex flex-col gap-1 rounded border border-filet bg-white p-4 text-encre";
  return href ? <Link href={href} className={cls}>{body}</Link> : <div className={cls}>{body}</div>;
}

export default function DashboardPage() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const params = new URLSearchParams({ ...(from && { date_from: from }), ...(to && { date_to: to }) });
  const { data: d, isLoading, error } = useQuery({
    queryKey: ["dashboard", from, to],
    queryFn: () => api<Dashboard>(`/admin/dashboard?${params}`),
  });

  return (
    <>
      <AdminTitle
        actions={
          <div className="flex items-end gap-2 text-sm">
            <label className="flex flex-col gap-1">Du<input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={`${inputClass} h-10`} /></label>
            <label className="flex flex-col gap-1">Au<input type="date" value={to} onChange={(e) => setTo(e.target.value)} className={`${inputClass} h-10`} /></label>
          </div>
        }
      >
        Tableau de bord
      </AdminTitle>
      {isLoading && <Loading />}
      {error && <Alert>{errorMessage(error)}</Alert>}
      {d && (
        <>
          {d.failed_emails > 0 && (
            <Alert>
              {d.failed_emails} e-mail{d.failed_emails > 1 ? "s n'ont" : " n'a"} pas pu être envoyé{d.failed_emails > 1 ? "s" : ""}.{" "}
              <Link href="/admin/emails" className="font-semibold underline">Voir et renvoyer</Link>
            </Alert>
          )}
          <p className="text-sm text-encre-douce">Période du {d.date_from} au {d.date_to} (30 derniers jours par défaut).</p>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
            <Kpi label="Chiffre d'affaires encaissé" value={formatFCFA(d.revenue)} />
            <Kpi label="Commandes livrées" value={String(d.delivered_orders)} />
            <Kpi label="Panier moyen" value={d.average_basket === null ? "—" : formatFCFA(d.average_basket)} />
            <Kpi label="Livraisons réussies" value={d.delivery_success_rate === null ? "—" : `${d.delivery_success_rate} %`} />
            <Kpi label="Frais de livraison" value={formatFCFA(d.delivery_fees)} />
            <Kpi label="Remises (codes promo)" value={formatFCFA(d.discounts)} href="/admin/codes-promo" />
            <Kpi label="Espèces chez les livreurs" value={formatFCFA(d.cash_held_by_couriers)} href="/admin/encaissements" />
            <Kpi label="Stocks bas" value={String(d.low_stock_variants)} href="/admin/stock?bas=1" />
            <Kpi label="Nouveaux messages" value={String(d.new_contact_messages)} href="/admin/messages" />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card title="À traiter maintenant">
              {Object.keys(d.to_process).length === 0 ? (
                <p className="text-sm text-encre-douce">Rien en attente.</p>
              ) : (
                <ul className="flex flex-col gap-2 text-sm">
                  {(Object.entries(d.to_process) as [OrderStatus, number][]).map(([s, n]) => (
                    <li key={s}><Link href={`/admin/commandes?statut=${s}`} className="flex justify-between"><span>{ORDER_STATUS[s]}</span><strong>{n}</strong></Link></li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title={`Commandes passées sur la période (${d.orders_created})`}>
              <ul className="flex flex-col gap-2 text-sm">
                {(Object.entries(d.orders_by_status) as [OrderStatus, number][]).map(([s, n]) => (
                  <li key={s} className="flex justify-between"><span>{ORDER_STATUS[s]}</span><strong>{n}</strong></li>
                ))}
              </ul>
            </Card>
            <Card title="Meilleures ventes">
              {d.best_sellers.length === 0 ? (
                <p className="text-sm text-encre-douce">Aucune vente livrée sur la période.</p>
              ) : (
                <ol className="flex flex-col gap-2 text-sm">
                  {d.best_sellers.map((b) => (
                    <li key={`${b.product_name}-${b.volume_ml}`} className="flex justify-between gap-2">
                      <span>{b.product_name} {b.volume_ml} ml</span><span>× {b.quantity}</span>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>
        </>
      )}
    </>
  );
}
