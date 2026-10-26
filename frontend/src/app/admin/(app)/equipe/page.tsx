"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { OwnerOnly } from "@/components/admin/owner-only";
import { AdminTitle, Card, Table, td } from "@/components/admin/ui";
import { Alert, Button, Field, inputClass } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatPhone, ROLE } from "@/lib/format";
import { normalizePhone } from "@/lib/schemas";
import type { Role, User } from "@/lib/types";

const STAFF_ROLES: Role[] = ["COURIER", "MANAGER", "OWNER"];
const EMPTY = { email: "", full_name: "", phone: "", role: "COURIER" as Role, temporary_password: "" };

export default function EquipePage() {
  const qc = useQueryClient();
  const staff = useQuery({ queryKey: ["staff"], queryFn: () => api<User[]>("/admin/staff") });
  const [form, setForm] = useState(EMPTY);
  const refresh = () => qc.invalidateQueries({ queryKey: ["staff"] });
  const create = useMutation({
    mutationFn: () => api<User>("/admin/staff", { json: { ...form, phone: normalizePhone(form.phone) } }),
    onSuccess: () => { setForm(EMPTY); refresh(); },
  });
  const update = useMutation({ mutationFn: ({ id, ...v }: { id: number; role?: Role; is_active?: boolean; reset_totp?: boolean }) => api(`/admin/staff/${id}`, { method: "PATCH", json: v }), onSuccess: refresh });
  const failure = create.error ?? update.error;
  const f = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  return (
    <OwnerOnly>
      <AdminTitle>Collaborateurs</AdminTitle>
      {failure && <Alert>{errorMessage(failure)}</Alert>}
      <Table head={["Nom", "E-mail", "Téléphone", "Rôle", "Double authentification", "Actif", ""]}>
        {staff.data?.map((u) => (
          <tr key={u.id}>
            <td className={td}>{u.full_name}</td>
            <td className={td}>{u.email}</td>
            <td className={td}>{formatPhone(u.phone)}</td>
            <td className={td}>
              <select value={u.role} aria-label={`Rôle de ${u.full_name}`} onChange={(e) => update.mutate({ id: u.id, role: e.target.value as Role })} className={`${inputClass} h-9`}>
                {STAFF_ROLES.map((r) => <option key={r} value={r}>{ROLE[r]}</option>)}
              </select>
            </td>
            <td className={td}>{u.role === "COURIER" ? "—" : u.totp_enabled ? "Active" : "À activer"}</td>
            <td className={td}><input type="checkbox" checked={u.is_active} aria-label={`${u.full_name} actif`} onChange={() => window.confirm(u.is_active ? `Désactiver ${u.full_name} ? Son accès est coupé immédiatement.` : `Réactiver ${u.full_name} ?`) && update.mutate({ id: u.id, is_active: !u.is_active })} className="h-5 w-5" /></td>
            <td className={td}>{u.totp_enabled && <Button size="sm" variant="ghost" onClick={() => window.confirm("Réinitialiser sa double authentification (téléphone perdu) ?") && update.mutate({ id: u.id, reset_totp: true })}>Réinitialiser la 2FA</Button>}</td>
          </tr>
        ))}
      </Table>
      <Card title="Ajouter un collaborateur">
        <form className="grid gap-3 md:grid-cols-3 md:items-end" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <Field label="Nom et prénom"><input value={form.full_name} onChange={f("full_name")} required minLength={2} className={inputClass} /></Field>
          <Field label="E-mail"><input type="email" value={form.email} onChange={f("email")} required className={inputClass} /></Field>
          <Field label="Téléphone"><input type="tel" value={form.phone} onChange={f("phone")} required className={inputClass} /></Field>
          <Field label="Rôle">
            <select value={form.role} onChange={f("role")} className={inputClass}>{STAFF_ROLES.map((r) => <option key={r} value={r}>{ROLE[r]}</option>)}</select>
          </Field>
          <Field label="Mot de passe provisoire" hint="10 caractères minimum, à lui transmettre de vive voix."><input value={form.temporary_password} onChange={f("temporary_password")} required minLength={10} autoComplete="new-password" className={inputClass} /></Field>
          <Button type="submit" disabled={create.isPending}>Créer</Button>
        </form>
      </Card>
    </OwnerOnly>
  );
}
