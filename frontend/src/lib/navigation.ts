import type { Role } from "./types";

/** Page d'accueil de chaque rôle après connexion. */
export function homeFor(role: Role): string {
  return role === "CUSTOMER" ? "/compte" : role === "COURIER" ? "/livreur" : "/admin";
}

/** Destination « suite » sûre : un chemin interne uniquement (pas de redirection ouverte). */
export function safeNext(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" && value.startsWith("/") && !value.startsWith("//") ? value : undefined;
}
