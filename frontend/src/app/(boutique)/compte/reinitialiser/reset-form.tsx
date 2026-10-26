"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";

export function ResetForm({ token }: { token: string }) {
  const [password, setPassword] = useState("");
  const reset = useMutation({ mutationFn: () => api<{ message: string }>("/auth/reset-password", { json: { token, password } }) });
  if (reset.isSuccess) {
    return (
      <Alert tone="success">
        {reset.data.message} <Link href="/compte/connexion" className="font-semibold underline">Se connecter</Link>
      </Alert>
    );
  }
  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); reset.mutate(); }}>
      <Field label="Nouveau mot de passe" hint="10 caractères minimum.">
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" minLength={10} required autoComplete="new-password" className={inputClass} />
      </Field>
      {reset.isError && <Alert>{errorMessage(reset.error)}</Alert>}
      <Button type="submit" disabled={reset.isPending || !token}>Enregistrer</Button>
    </form>
  );
}
