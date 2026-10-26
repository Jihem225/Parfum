import type { ReactNode } from "react";

export function AdminTitle({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="font-display text-[30px]">{children}</h1>
      {actions}
    </div>
  );
}

export function Card({ title, children, className = "" }: { title?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`flex flex-col gap-3 rounded border border-filet bg-white p-5 ${className}`}>
      {title && <h2 className="text-base font-bold">{title}</h2>}
      {children}
    </section>
  );
}

/** Tableau lisible sur mobile : défilement horizontal plutôt que débordement de page. */
export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded border border-filet bg-white">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-b border-filet bg-surface text-xs uppercase tracking-wide text-encre-douce">
          <tr>{head.map((h, i) => <th key={i} className="px-3 py-2.5 font-semibold">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-filet">{children}</tbody>
      </table>
    </div>
  );
}

export const td = "px-3 py-2.5 align-top";
