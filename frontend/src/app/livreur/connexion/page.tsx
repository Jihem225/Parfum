import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/components/compte/login-form";
import { safeNext } from "@/lib/navigation";

export const metadata: Metadata = { title: "Connexion livreur", robots: { index: false } };

export default function LivreurConnexionPage({ searchParams }: PageProps<"/livreur/connexion">) {
  return (
    <main className="flex flex-1 items-center justify-center bg-admin p-4">
      <div className="flex w-full max-w-sm flex-col gap-5 rounded border border-filet bg-white p-6">
        <h1 className="font-display text-[26px]">Espace livreur</h1>
        <Suspense>{searchParams.then((p) => <LoginForm staff next={safeNext(p.suite)} />)}</Suspense>
      </div>
    </main>
  );
}
