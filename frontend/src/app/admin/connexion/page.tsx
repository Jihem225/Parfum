import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/components/compte/login-form";
import { safeNext } from "@/lib/navigation";

export const metadata: Metadata = { title: "Connexion collaborateur", robots: { index: false } };

export default function AdminConnexionPage({ searchParams }: PageProps<"/admin/connexion">) {
  return (
    <main className="flex flex-1 items-center justify-center bg-admin p-4">
      <div className="flex w-full max-w-sm flex-col gap-5 rounded border border-filet bg-white p-6">
        <div>
          <div className="font-display text-[15px] tracking-[0.22em]">PROJET PARFUMS</div>
          <h1 className="mt-2 text-xl font-bold">Espace collaborateurs</h1>
        </div>
        <Suspense>{searchParams.then((p) => <LoginForm staff next={safeNext(p.suite)} />)}</Suspense>
      </div>
    </main>
  );
}
