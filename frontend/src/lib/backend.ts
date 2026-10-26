// URL du backend FastAPI, connue du serveur Next.js uniquement (jamais exposée au navigateur).
export const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
