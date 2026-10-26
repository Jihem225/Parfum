"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import type { z } from "zod";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, ApiError, errorMessage } from "@/lib/api";
import { registerSchema } from "@/lib/schemas";
import type { User } from "@/lib/types";

type In = z.input<typeof registerSchema>;
type Out = z.output<typeof registerSchema>;

export default function InscriptionPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { register, handleSubmit, setError, formState: { errors } } = useForm<In, unknown, Out>({ resolver: zodResolver(registerSchema) });
  const signup = useMutation({
    mutationFn: (v: Out) => api<User>("/auth/register", { json: v }),
    onSuccess: () => {
      qc.clear(); // le panier visiteur a rejoint le compte
      router.push("/compte");
    },
    onError: (e) => {
      if (!(e instanceof ApiError)) return;
      for (const [field, message] of Object.entries(e.fieldErrors())) setError(field as keyof In, { message });
      if (e.code === "EMAIL_TAKEN") setError("email", { message: e.message });
    },
  });
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 py-8">
      <h1 className="font-display text-[32px]">Créer un compte</h1>
      <form onSubmit={handleSubmit((v) => signup.mutate(v))} noValidate className="flex flex-col gap-4">
        <Field label="Nom et prénom" error={errors.full_name?.message}>
          <input {...register("full_name")} autoComplete="name" className={inputClass} aria-invalid={!!errors.full_name} />
        </Field>
        <Field label="E-mail" error={errors.email?.message}>
          <input {...register("email")} type="email" autoComplete="email" className={inputClass} aria-invalid={!!errors.email} />
        </Field>
        <Field label="Téléphone" error={errors.phone?.message}>
          <input {...register("phone")} type="tel" inputMode="tel" autoComplete="tel" placeholder="07 08 12 34 56" className={inputClass} aria-invalid={!!errors.phone} />
        </Field>
        <Field label="Mot de passe" hint="10 caractères minimum." error={errors.password?.message}>
          <input {...register("password")} type="password" autoComplete="new-password" className={inputClass} aria-invalid={!!errors.password} />
        </Field>
        {signup.isError && !(signup.error instanceof ApiError && signup.error.code === "EMAIL_TAKEN") && <Alert>{errorMessage(signup.error)}</Alert>}
        <Button type="submit" disabled={signup.isPending}>{signup.isPending ? "Création…" : "Créer mon compte"}</Button>
      </form>
      <p className="text-sm">
        Déjà un compte ? <Link href="/compte/connexion" className="font-semibold underline underline-offset-4">Se connecter</Link>
      </p>
    </div>
  );
}
