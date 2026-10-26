import { z } from "zod";

// Pré-validation côté navigateur ; le serveur reste seul juge (mêmes règles que le backend).

/** « +225 07 08 12 34 56 » → « 0708123456 ». Mobiles en 0…, fixes en 2… (plan à 10 chiffres). */
export function normalizePhone(value: string): string {
  return value.replace(/[\s.\-()]/g, "").replace(/^(\+|00)225/, "");
}

export const phone = z
  .string()
  .transform(normalizePhone)
  .refine((v) => /^[02]\d{9}$/.test(v), "Numéro ivoirien attendu : 10 chiffres, par exemple 07 08 12 34 56.");

const optionalEmail = z
  .string()
  .trim()
  .refine((v) => v === "" || z.email().safeParse(v).success, "Adresse e-mail invalide.");

export const personName = z.string().trim().min(2, "Indiquez votre nom.").max(120);
export const password = z.string().min(10, "10 caractères minimum.").max(128);

export const checkoutSchema = z.object({
  customer_name: personName,
  phone,
  email: optionalEmail,
  commune_id: z.coerce.number<string>().int().positive("Choisissez votre commune."),
  address_line: z.string().trim().min(3, "Indiquez votre adresse (quartier, rue, bâtiment).").max(255),
  landmark: z.string().trim().max(255),
  accept_terms: z.boolean().refine((v) => v, "Vous devez accepter les conditions générales de vente."),
});
export type CheckoutValues = z.input<typeof checkoutSchema>;

export const loginSchema = z.object({
  email: z.email("Adresse e-mail invalide.").trim(),
  password: z.string().min(1, "Saisissez votre mot de passe."),
  totp_code: z.string().trim().optional(),
});

export const registerSchema = z.object({
  full_name: personName,
  email: z.email("Adresse e-mail invalide.").trim(),
  phone,
  password,
});

export const contactSchema = z
  .object({ name: personName, phone: z.string().trim(), email: optionalEmail, message: z.string().trim().min(10, "10 caractères minimum.").max(2000) })
  .refine((v) => v.phone || v.email, { message: "Indiquez un téléphone ou un e-mail pour que nous puissions répondre.", path: ["phone"] })
  .refine((v) => !v.phone || phone.safeParse(v.phone).success, { message: "Numéro ivoirien attendu : 10 chiffres.", path: ["phone"] });
