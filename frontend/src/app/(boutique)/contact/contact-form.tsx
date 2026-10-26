"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import type { z } from "zod";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { contactSchema, normalizePhone } from "@/lib/schemas";

type Values = z.input<typeof contactSchema>;

export function ContactForm() {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<Values>({
    resolver: zodResolver(contactSchema),
    defaultValues: { name: "", phone: "", email: "", message: "" },
  });
  const send = useMutation({
    mutationFn: (v: Values) =>
      api<{ message: string }>("/contact", {
        json: { name: v.name, message: v.message, phone: v.phone ? normalizePhone(v.phone) : null, email: v.email || null },
      }),
    onSuccess: () => reset(),
  });
  return (
    <form onSubmit={handleSubmit((v) => send.mutate(v))} noValidate className="flex flex-col gap-4">
      <Field label="Nom" error={errors.name?.message}>
        <input {...register("name")} autoComplete="name" className={inputClass} />
      </Field>
      <Field label="Téléphone" error={errors.phone?.message}>
        <input {...register("phone")} type="tel" inputMode="tel" autoComplete="tel" className={inputClass} />
      </Field>
      <Field label="E-mail" error={errors.email?.message}>
        <input {...register("email")} type="email" autoComplete="email" className={inputClass} />
      </Field>
      <Field label="Message" error={errors.message?.message}>
        <textarea {...register("message")} rows={5} className={`${inputClass} h-auto py-2`} />
      </Field>
      {send.isSuccess && <Alert tone="success">{send.data.message}</Alert>}
      {send.isError && <Alert>{errorMessage(send.error)}</Alert>}
      <Button type="submit" disabled={send.isPending}>{send.isPending ? "Envoi…" : "Envoyer"}</Button>
    </form>
  );
}
