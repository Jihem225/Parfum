"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { OrderView } from "@/components/order-view";
import { Alert, Button, Loading } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import type { Order } from "@/lib/types";

export default function MaCommandePage() {
  const { number } = useParams<{ number: string }>();
  const qc = useQueryClient();
  const order = useQuery({ queryKey: ["my-order", number], queryFn: () => api<Order>(`/me/orders/${number}`) });
  const cancel = useMutation({
    mutationFn: () => api<Order>(`/me/orders/${number}/cancel`, { json: {} }),
    onSuccess: (o) => {
      qc.setQueryData(["my-order", number], o);
      qc.invalidateQueries({ queryKey: ["my-orders"] });
    },
  });
  if (order.isLoading) return <Loading />;
  if (order.error || !order.data) return <Alert>{errorMessage(order.error)}</Alert>;
  return (
    <div className="flex flex-col gap-6">
      <Link href="/compte/commandes" className="text-sm underline underline-offset-4">← Mes commandes</Link>
      <OrderView order={order.data} />
      {cancel.isError && <Alert>{errorMessage(cancel.error)}</Alert>}
      {order.data.can_cancel && (
        <Button
          variant="secondary"
          disabled={cancel.isPending}
          onClick={() => {
            const paid = order.data?.payment_method === "MOBILE_MONEY" && order.data.status !== "EN_ATTENTE_PAIEMENT";
            if (window.confirm(paid ? "Annuler cette commande ? La boutique vous remboursera votre paiement." : "Annuler cette commande ?")) cancel.mutate();
          }}
        >
          Annuler la commande
        </Button>
      )}
    </div>
  );
}
