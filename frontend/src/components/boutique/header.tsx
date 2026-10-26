import Link from "next/link";
import { AccountLink, CartLink } from "./header-links";

const NAV = [
  { href: "/parfums", label: "Parfums" },
  { href: "/collections", label: "Collections" },
  { href: "/suivi", label: "Suivre ma commande" },
  { href: "/contact", label: "Contact" },
];

export function Header() {
  return (
    <>
      <div className="bg-encre px-4 py-2 text-center text-xs tracking-[0.02em] text-porcelaine">
        Livraison à Abidjan · Paiement à la livraison
      </div>
      <header className="sticky top-0 z-20 border-b border-filet bg-porcelaine">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-1.5 md:px-4">
          {/* Menu mobile sans JavaScript : <details> natif. */}
          <details className="relative md:hidden">
            <summary className="flex h-11 w-11 cursor-pointer list-none items-center justify-center" aria-label="Menu">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
                <path d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </summary>
            <nav className="absolute left-0 top-12 flex w-64 flex-col border border-filet bg-porcelaine p-2 shadow-lg">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href} className="px-3 py-3 text-[15px]">
                  {n.label}
                </Link>
              ))}
            </nav>
          </details>
          <Link href="/" className="font-display text-base tracking-[0.24em] text-encre">
            PROJET PARFUMS
          </Link>
          <nav className="hidden gap-6 text-sm font-semibold md:flex" aria-label="Navigation principale">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href}>
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="flex">
            <Link href="/parfums" aria-label="Rechercher" className="inline-flex h-11 w-11 items-center justify-center">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
                <circle cx="11" cy="11" r="6" />
                <path d="m20 20-4.5-4.5" />
              </svg>
            </Link>
            <AccountLink />
            <CartLink />
          </div>
        </div>
      </header>
    </>
  );
}
