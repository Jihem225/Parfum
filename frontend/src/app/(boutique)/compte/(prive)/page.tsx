"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatPhone } from "@/lib/format";
import { useMe } from "@/lib/hooks";
import { normalizePhone } from "@/lib/schemas";
import type { User } from "@/lib/types";

export default function ComptePage() {
  const { data: me } = useMe();
  const qc = useQueryClient();
  const [name, setName] = useState(me?.full_name ?? "");
  const [phone, setPhone] = useState(me ? formatPhone(me.phone) : "");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const profile = useMutation({
    mutationFn: () => api<User>("/me/profile", { method: "PATCH", json: { full_name: name, phone: normalizePhone(phone) } }),
    onSuccess: (user) => qc.setQueryData(["me"], user),
  });
  const password = useMutation({
    mutationFn: () => api<{ message: string }>("/auth/change-password", { json: { current_password: current, new_password: next } }),
    onSuccess: () => {
      setCurrent("");
      setNext("");
    },
  });
  if (!me) return null;
  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-display text-[32px]">Bonjour {me.full_name.split(" ")[0]}</h1>
      <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); profile.mutate(); }}>
        <h2 className="font-display text-[22px]">Mes informations</h2>
        <Field label="E-mail" hint="L'e-mail sert d'identifiant et ne peut pas être modifié ici.">
          <input value={me.email} disabled className={`${inputClass} bg-surface`} />
        </Field>
        <Field label="Nom et prénom">
          <input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} className={inputClass} />
        </Field>
        <Field label="Téléphone">
          <input value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" required className={inputClass} />
        </Field>
        {profile.isSuccess && <Alert tone="success">Informations enregistrées.</Alert>}
        {profile.isError && <Alert>{errorMessage(profile.error)}</Alert>}
        <Button type="submit" disabled={profile.isPending}>Enregistrer</Button>
      </form>
      <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); password.mutate(); }}>
        <h2 className="font-display text-[22px]">Mot de passe</h2>
        <Field label="Mot de passe actuel">
          <input value={current} onChange={(e) => setCurrent(e.target.value)} type="password" required autoComplete="current-password" className={inputClass} />
        </Field>
        <Field label="Nouveau mot de passe" hint="10 caractères minimum.">
          <input value={next} onChange={(e) => setNext(e.target.value)} type="password" required minLength={10} autoComplete="new-password" className={inputClass} />
        </Field>
        {password.isSuccess && <Alert tone="success">{password.data.message}</Alert>}
        {password.isError && <Alert>{errorMessage(password.error)}</Alert>}
        <Button type="submit" variant="secondary" disabled={password.isPending}>Changer le mot de passe</Button>
      </form>
    </div>
  );
}
