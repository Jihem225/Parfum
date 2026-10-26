import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { LoginForm } from "@/components/compte/login-form";
import { safeNext } from "@/lib/navigation";

export const metadata: Metadata = { title: "Connexion", robots: { index: false } };

export default function ConnexionPage({ searchParams }: PageProps<"/compte/connexion">) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 py-8">
      <h1 className="font-display text-[32px]">Connexion</h1>
      <Suspense>{searchParams.then((p) => <LoginForm next={safeNext(p.suite)} />)}</Suspense>
      <div className="flex flex-col gap-2 text-sm">
        <Link href="/compte/mot-de-passe-oublie" className="underline underline-offset-4">Mot de passe oublié ?</Link>
        <span>
          Pas encore de compte ? <Link href="/compte/inscription" className="font-semibold underline underline-offset-4">Créer un compte</Link>
        </span>
        <span className="text-encre-douce">Un compte n&apos;est pas nécessaire pour commander.</span>
      </div>
    </div>
  );
}
