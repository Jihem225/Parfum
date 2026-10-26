"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { homeFor } from "@/lib/navigation";
import { useMe } from "@/lib/hooks";

const TABS = [
  ["/compte", "Mon compte"],
  ["/compte/commandes", "Mes commandes"],
  ["/compte/adresses", "Mes adresses"],
] as const;

export function CompteShell({ children }: { children: React.ReactNode }) {
  const { data: me, isLoading } = useMe();
  const router = useRouter();
  const pathname = usePathname();
  const qc = useQueryClient();

  useEffect(() => {
    if (isLoading) return;
    if (!me) router.replace(`/compte/connexion?suite=${encodeURIComponent(pathname)}`);
    else if (me.role !== "CUSTOMER") router.replace(homeFor(me.role));
  }, [me, isLoading, pathname, router]);

  if (!me || me.role !== "CUSTOMER") return <Loading />;
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6">
      <nav className="flex flex-wrap gap-2 border-b border-filet pb-3 text-sm" aria-label="Mon compte">
        {TABS.map(([href, label]) => (
          <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined} className="rounded-full px-3 py-2 font-semibold aria-[current=page]:bg-encre aria-[current=page]:text-porcelaine">
            {label}
          </Link>
        ))}
        <button
          type="button"
          className="ml-auto px-3 py-2 underline underline-offset-4"
          onClick={async () => {
            await api("/auth/logout", { method: "POST" });
            qc.clear();
            router.push("/");
          }}
        >
          Se déconnecter
        </button>
      </nav>
      {children}
    </div>
  );
}
