"use client";

import { Alert } from "@/components/ui";
import { useMe } from "@/lib/hooks";

/** Écrans du Propriétaire : masqués ici, refusés par le serveur de toute façon. */
export function OwnerOnly({ children }: { children: React.ReactNode }) {
  const { data: me } = useMe();
  if (me?.role !== "OWNER") return <Alert>Cette page est réservée au Propriétaire.</Alert>;
  return <>{children}</>;
}
