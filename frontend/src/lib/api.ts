// Client HTTP du navigateur : passe par le relais /api/v1 (même origine, cookies httpOnly).

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: unknown,
  ) {
    super(message);
  }

  /** Erreurs de champ de la validation serveur : { champ: message }. */
  fieldErrors(): Record<string, string> {
    if (this.code !== "VALIDATION_ERROR" || !Array.isArray(this.details)) return {};
    const out: Record<string, string> = {};
    for (const d of this.details as { field?: string; message?: string }[]) {
      if (d.field && d.message && !(d.field in out)) out[d.field] = d.message;
    }
    return out;
  }
}

const BASE = "/api/v1";

function readCookie(name: string): string | undefined {
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`))
    ?.slice(name.length + 1);
}

// Double soumission CSRF : le cookie `csrf` (lisible) est renvoyé en en-tête.
async function csrfToken(): Promise<string> {
  if (!readCookie("csrf")) await fetch(`${BASE}/health`, { credentials: "same-origin" });
  return readCookie("csrf") ?? "";
}

type Options = { method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"; json?: unknown; form?: FormData };

export async function api<T>(path: string, { method, json, form }: Options = {}): Promise<T> {
  const verb = method ?? (json !== undefined || form ? "POST" : "GET");
  const headers: Record<string, string> = {};
  if (verb !== "GET") headers["X-CSRF-Token"] = await csrfToken();
  let body: BodyInit | undefined;
  if (form) body = form;
  else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }
  let res: Response;
  try {
    res = await fetch(BASE + path, { method: verb, headers, body, credentials: "same-origin" });
  } catch {
    throw new ApiError(0, "NETWORK", "Connexion impossible. Vérifiez votre réseau et réessayez.");
  }
  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const e = (data as { error?: { code?: string; message?: string; details?: unknown } } | null)?.error;
    throw new ApiError(
      res.status,
      e?.code ?? "HTTP_ERROR",
      e?.message ?? "Une erreur est survenue. Réessayez.",
      e?.details,
    );
  }
  return data as T;
}

/** Message lisible pour n'importe quelle erreur attrapée. */
export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Une erreur est survenue. Réessayez.";
}
