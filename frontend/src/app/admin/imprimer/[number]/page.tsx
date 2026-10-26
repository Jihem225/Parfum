import type { Metadata } from "next";
import { Suspense } from "react";
import { PrintDocument } from "./print-document";

export const metadata: Metadata = { title: "Impression", robots: { index: false } };

export default function ImprimerPage({ params, searchParams }: PageProps<"/admin/imprimer/[number]">) {
  return (
    <main className="mx-auto w-full max-w-2xl bg-white p-6 text-encre">
      <Suspense>
        {Promise.all([params, searchParams]).then(([p, s]) => (
          <PrintDocument number={p.number} doc={s.doc === "bordereau" ? "bordereau" : "bon"} />
        ))}
      </Suspense>
    </main>
  );
}
