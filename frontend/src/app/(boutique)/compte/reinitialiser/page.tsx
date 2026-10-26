import type { Metadata } from "next";
import { Suspense } from "react";
import { ResetForm } from "./reset-form";

export const metadata: Metadata = { title: "Nouveau mot de passe", robots: { index: false } };

export default function ReinitialiserPage({ searchParams }: PageProps<"/compte/reinitialiser">) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 py-8">
      <h1 className="font-display text-[32px]">Nouveau mot de passe</h1>
      <Suspense>{searchParams.then((p) => <ResetForm token={typeof p.token === "string" ? p.token : ""} />)}</Suspense>
    </div>
  );
}
