"use client";

import Link from "next/link";
import { useCart, useMe } from "@/lib/hooks";

export function CartLink() {
  const { data } = useCart();
  const count = data?.item_count ?? 0;
  return (
    <Link
      href="/panier"
      aria-label={count ? `Panier, ${count} article${count > 1 ? "s" : ""}` : "Panier"}
      className="relative inline-flex h-11 w-11 items-center justify-center"
    >
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
        <path d="M5 8h14l-1 12H6L5 8Z" />
        <path d="M9 8V6a3 3 0 0 1 6 0v2" />
      </svg>
      {count > 0 && (
        <span className="absolute right-1 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-safran px-1 text-[10px] font-bold text-white">
          {count}
        </span>
      )}
    </Link>
  );
}

export function AccountLink() {
  const { data: me } = useMe();
  const href = !me ? "/compte/connexion" : me.role === "CUSTOMER" ? "/compte" : me.role === "COURIER" ? "/livreur" : "/admin";
  return (
    <Link href={href} aria-label={me ? "Mon compte" : "Se connecter"} className="inline-flex h-11 w-11 items-center justify-center">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" />
      </svg>
    </Link>
  );
}
