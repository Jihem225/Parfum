import { formatDateTime, formatFCFA, formatPhone, ORDER_STATUS } from "@/lib/format";
import type { Order } from "@/lib/types";
import { PayButton } from "./pay-button";
import { Alert, StatusPill } from "./ui";

function totalLabel(order: Order): string {
  if (order.payment_method === "CASH_ON_DELIVERY") return "Total à payer en espèces à la livraison";
  if (order.status === "EN_ATTENTE_PAIEMENT") return "Total à payer par mobile money";
  return order.status === "ANNULEE" ? "Total" : "Total payé par mobile money";
}

/** Détail d'une commande côté client : copie figée (RG-26) et chronologie des statuts. */
export function OrderView({ order }: { order: Order }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-bold tracking-[0.02em]">{order.number}</h2>
        <StatusPill status={order.status} />
        <span className="text-sm text-encre-douce">passée le {formatDateTime(order.created_at)}</span>
      </div>

      {order.payment_token && (
        <div className="flex flex-col gap-3">
          <Alert tone="info">Cette commande attend votre paiement. Sans paiement dans les 30 minutes suivant la commande, elle est annulée.</Alert>
          <PayButton number={order.number} token={order.payment_token} label={`Payer ${formatFCFA(order.total)}`} />
        </div>
      )}

      <ol className="flex flex-col border-l-2 border-filet pl-4" aria-label="Historique">
        {order.history.map((h, i) => (
          <li key={i} className="relative pb-4 last:pb-0">
            <span className={`absolute -left-[23px] top-1 h-3 w-3 rounded-full ${i === order.history.length - 1 ? "bg-encre" : "bg-filet"}`} aria-hidden />
            <div className="font-semibold">{ORDER_STATUS[h.status]}</div>
            <div className="text-sm text-encre-douce">{formatDateTime(h.at)}</div>
          </li>
        ))}
      </ol>

      <section className="flex flex-col gap-2 text-sm">
        {order.items.map((i) => (
          <div key={i.sku} className="flex justify-between gap-4">
            <span>
              {i.product_name} · {i.volume_ml} ml × {i.quantity}
            </span>
            <span>{formatFCFA(i.line_total)}</span>
          </div>
        ))}
        {order.discount > 0 && (
          <div className="flex justify-between text-encre-douce">
            <span>Code {order.promo_code}</span>
            <span>−{formatFCFA(order.discount)}</span>
          </div>
        )}
        <div className="flex justify-between text-encre-douce">
          <span>Livraison ({order.commune_name}, {order.delivery_delay_label})</span>
          <span>{formatFCFA(order.delivery_fee)}</span>
        </div>
        <div className="flex justify-between border-t border-filet pt-2 text-base font-bold">
          <span>{totalLabel(order)}</span>
          <span>{formatFCFA(order.total)}</span>
        </div>
      </section>

      <section className="bg-surface p-4 text-sm leading-relaxed">
        <div className="font-semibold">{order.customer_name}</div>
        <div>{formatPhone(order.phone)}</div>
        <div>
          {order.address_line}, {order.commune_name}
        </div>
        {order.landmark && <div className="text-encre-douce">Repère : {order.landmark}</div>}
      </section>
    </div>
  );
}
