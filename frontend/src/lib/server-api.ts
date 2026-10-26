import { BACKEND_URL } from "./backend";

// Lecture des données publiques depuis les composants serveur (URL interne, sans cookies).
// Appelée au moment de la requête, dans un <Suspense> : le build ne dépend pas de l'API.
export async function getPublic<T>(path: string): Promise<T | null> {
  const res = await fetch(`${BACKEND_URL}/api/v1${path}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status} sur ${path}`);
  return (await res.json()) as T;
}
