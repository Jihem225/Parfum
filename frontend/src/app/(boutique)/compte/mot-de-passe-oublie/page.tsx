"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";

export default function MotDePasseOubliePage() {
  const [email, setEmail] = useState("");
  const send = useMutation({ mutationFn: () => api<{ message: string }>("/auth/forgot-password", { json: { email } }) });
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 py-8">
      <h1 className="font-display text-[32px]">Mot de passe oublié</h1>
      <p className="text-sm text-encre-douce">Indiquez votre e-mail : vous recevrez un lien valable 1 heure.</p>
      <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); send.mutate(); }}>
        <Field label="E-mail">
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoComplete="email" className={inputClass} />
        </Field>
        {/* Même réponse que le compte existe ou non (pas d'énumération des e-mails). */}
        {send.isSuccess && <Alert tone="success">{send.data.message}</Alert>}
        {send.isError && <Alert>{errorMessage(send.error)}</Alert>}
        <Button type="submit" disabled={send.isPending}>Envoyer le lien</Button>
      </form>
    </div>
  );
}
