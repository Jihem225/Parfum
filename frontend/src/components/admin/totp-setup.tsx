"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";

/** Activation obligatoire de la double authentification (Propriétaire, Gestionnaire). */
export function TotpSetup() {
  const qc = useQueryClient();
  const [code, setCode] = useState("");
  const setup = useMutation({ mutationFn: () => api<{ secret: string; otpauth_uri: string }>("/auth/totp/setup", { method: "POST" }) });
  const enable = useMutation({
    mutationFn: () => api<{ recovery_codes: string[] }>("/auth/totp/enable", { json: { secret: setup.data?.secret, code } }),
  });

  if (enable.data) {
    return (
      <div className="flex max-w-lg flex-col gap-4">
        <h1 className="font-display text-[30px]">Double authentification active</h1>
        <Alert tone="info">Notez ces codes de secours et rangez-les en lieu sûr : chacun permet une connexion si vous perdez votre téléphone. Ils ne seront plus affichés.</Alert>
        <ul className="grid grid-cols-2 gap-2 font-mono text-lg">
          {enable.data.recovery_codes.map((c) => <li key={c} className="bg-surface px-3 py-2">{c}</li>)}
        </ul>
        <Button onClick={() => qc.invalidateQueries({ queryKey: ["me"] })}>J&apos;ai noté mes codes</Button>
      </div>
    );
  }
  return (
    <div className="flex max-w-lg flex-col gap-4">
      <h1 className="font-display text-[30px]">Sécurisez votre accès</h1>
      <p>L&apos;administration exige la double authentification : un code à 6 chiffres donné par une application (Google Authenticator, Microsoft Authenticator…) en plus du mot de passe.</p>
      {!setup.data ? (
        <Button onClick={() => setup.mutate()} disabled={setup.isPending}>Commencer</Button>
      ) : (
        <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); enable.mutate(); }}>
          <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm">
            <li>
              Sur ce téléphone, <a href={setup.data.otpauth_uri} className="font-semibold underline">ouvrez ce lien</a> ; sinon, dans l&apos;application, ajoutez un compte avec la clé :
              <code className="mt-1 block break-all bg-surface px-3 py-2 font-mono text-base">{setup.data.secret}</code>
            </li>
            <li>Saisissez le code à 6 chiffres affiché.</li>
          </ol>
          <Field label="Code">
            <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" required className={inputClass} />
          </Field>
          {enable.isError && <Alert>{errorMessage(enable.error)}</Alert>}
          <Button type="submit" disabled={enable.isPending}>Activer</Button>
        </form>
      )}
      {setup.isError && <Alert>{errorMessage(setup.error)}</Alert>}
    </div>
  );
}
