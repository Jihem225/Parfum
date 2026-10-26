"use client";

import { useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { homeFor } from "@/lib/navigation";
import { useMe } from "@/lib/hooks";

export function LivreurShell({ children }: { children: React.ReactNode }) {
  const { data: me, isLoading } = useMe();
  const router = useRouter();
  const pathname = usePathname();
  const qc = useQueryClient();
  const allowed = me && me.role !== "CUSTOMER";

  useEffect(() => {
    if (isLoading) return;
    if (!me) router.replace(`/livreur/connexion?suite=${encodeURIComponent(pathname)}`);
    else if (!allowed) router.replace(homeFor(me.role));
  }, [me, isLoading, allowed, pathname, router]);

  if (!me || !allowed) return <Loading />;
  return (
    <div className="flex min-h-screen flex-col bg-admin">
      <header className="flex h-14 items-center justify-between bg-encre px-4 text-porcelaine">
        <span className="font-display tracking-[0.2em]">LIVRAISONS</span>
        <button
          type="button"
          className="text-sm underline underline-offset-4"
          onClick={async () => {
            await api("/auth/logout", { method: "POST" });
            qc.clear();
            router.push("/livreur/connexion");
          }}
        >
          {me.full_name.split(" ")[0]} · Quitter
        </button>
      </header>
      <main className="mx-auto flex w-full max-w-lg flex-col gap-4 p-4">{children}</main>
    </div>
  );
}
