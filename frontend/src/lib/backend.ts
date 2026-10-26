// URL du backend FastAPI, connue du serveur Next.js uniquement (jamais exposée au navigateur).
// Render la fournit sans schéma (« hôte:port » du réseau privé).
const raw = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
export const BACKEND_URL = raw.includes("://") ? raw : `http://${raw}`;
