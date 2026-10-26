"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import type { z } from "zod";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, ApiError, errorMessage } from "@/lib/api";
import { homeFor } from "@/lib/navigation";
import { loginSchema } from "@/lib/schemas";
import type { User } from "@/lib/types";

type Values = z.infer<typeof loginSchema>;

/** Connexion commune (client, back-office, livreur). Le code de double authentification
 * apparaît quand le serveur le demande (Propriétaire, Gestionnaire). */
export function LoginForm({ next, staff = false }: { next?: string; staff?: boolean }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [askCode, setAskCode] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<Values>({ resolver: zodResolver(loginSchema) });
  const login = useMutation({
    mutationFn: (v: Values) => api<User>("/auth/login", { json: { ...v, totp_code: v.totp_code || null } }),
    onSuccess: async (user) => {
      qc.clear();
      router.push(next ?? homeFor(user.role));
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === "TOTP_REQUIRED") setAskCode(true);
    },
  });
  const needCode = login.error instanceof ApiError && login.error.code === "TOTP_REQUIRED";
  return (
    <form onSubmit={handleSubmit((v) => login.mutate(v))} noValidate className="flex flex-col gap-4">
      <Field label="E-mail" error={errors.email?.message}>
        <input {...register("email")} type="email" autoComplete={staff ? "username" : "email"} className={inputClass} aria-invalid={!!errors.email} />
      </Field>
      <Field label="Mot de passe" error={errors.password?.message}>
        <input {...register("password")} type="password" autoComplete="current-password" className={inputClass} aria-invalid={!!errors.password} />
      </Field>
      {askCode && (
        <Field label="Code de double authentification" hint="6 chiffres de votre application, ou un code de secours.">
          <input {...register("totp_code")} inputMode="numeric" autoComplete="one-time-code" autoFocus className={inputClass} />
        </Field>
      )}
      {login.isError && !needCode && <Alert>{errorMessage(login.error)}</Alert>}
      {needCode && <Alert tone="info">Saisissez le code de votre application d&apos;authentification.</Alert>}
      <Button type="submit" disabled={login.isPending}>{login.isPending ? "Connexion…" : "Se connecter"}</Button>
    </form>
  );
}
