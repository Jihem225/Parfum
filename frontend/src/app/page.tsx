import { Suspense } from "react";
import { connection } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

// Page provisoire de l'étape 5 : prouve que le frontend joint l'API. Remplacée à l'étape 7.
async function ApiStatus() {
  await connection();
  const ok = await fetch(`${BACKEND_URL}/api/v1/health`)
    .then((res) => res.ok)
    .catch(() => false);
  return (
    <p className={ok ? "text-succes" : "text-erreur"}>API : {ok ? "connectée" : "injoignable"}</p>
  );
}

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="font-display text-4xl tracking-[0.2em]">PROJET PARFUMS</h1>
      <p className="text-encre-douce">Initialisation du projet — la boutique arrive.</p>
      <Suspense fallback={<p className="text-encre-douce">API : vérification…</p>}>
        <ApiStatus />
      </Suspense>
    </main>
  );
}
