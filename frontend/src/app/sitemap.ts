import type { MetadataRoute } from "next";
import { connection } from "next/server";
import { getPublic } from "@/lib/server-api";
import type { Collection, Page, ProductCard } from "@/lib/types";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  await connection(); // construit à la demande : le build ne dépend pas de l'API
  const [products, collections] = await Promise.all([
    getPublic<Page<ProductCard>>("/catalog/products?page_size=48").catch(() => null),
    getPublic<Collection[]>("/catalog/collections").catch(() => null),
  ]);
  // shortcut: une seule page de 48 parfums ; paginer au-delà de 48 parfums publiés.
  return [
    ...["", "/parfums", "/collections", "/contact", "/infos/livraison", "/infos/faq"].map((p) => ({ url: `${SITE}${p}` })),
    ...(products?.items ?? []).map((p) => ({ url: `${SITE}/parfums/${p.slug}` })),
    ...(collections ?? []).map((c) => ({ url: `${SITE}/collections/${c.slug}` })),
  ];
}
