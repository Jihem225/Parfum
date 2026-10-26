"use client";

import { Button } from "@/components/ui";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="font-display text-3xl">Un problème est survenu</h1>
      <p className="text-encre-douce">Le service est momentanément indisponible. Réessayez dans un instant.</p>
      <Button onClick={reset}>Réessayer</Button>
    </main>
  );
}
