import Form from "next/form";
import Link from "next/link";
import { inputClass, buttonClass } from "@/components/ui";
import { formatFCFA, GENDER } from "@/lib/format";
import { getPublic } from "@/lib/server-api";
import type { Collection, Family, Page, ProductCard } from "@/lib/types";
import { ProductGrid } from "./product-card";

type Params = Record<string, string | string[] | undefined>;

const KEYS = ["q", "collection", "family", "gender", "max_price", "volume", "in_stock", "sort", "page"] as const;
const SORTS = { nouveautes: "Nouveautés", popularite: "Popularité", prix_croissant: "Prix croissant", prix_decroissant: "Prix décroissant" };
const PRICES = [25000, 50000, 100000];
const VOLUMES = [30, 50, 75, 100];

function pick(params: Params): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of KEYS) {
    const v = params[k];
    if (typeof v === "string" && v) out[k] = v;
  }
  return out;
}

const qs = (p: Record<string, string>) => new URLSearchParams(p).toString();

/** Catalogue filtrable (F-02 à F-06). Les filtres sont dans l'URL : lien partageable (US-01). */
export async function Catalogue({ searchParams, basePath, collection }: {
  searchParams: Promise<Params>;
  basePath: string;
  collection?: string;
}) {
  const current = pick(await searchParams);
  const query = { ...current, ...(collection ? { collection } : {}), page_size: "24" };
  const [page, families, collections] = await Promise.all([
    getPublic<Page<ProductCard>>(`/catalog/products?${qs(query)}`),
    getPublic<Family[]>("/catalog/families"),
    getPublic<Collection[]>("/catalog/collections"),
  ]);
  if (!page) return null;
  const active = Object.entries(current).filter(([k]) => k !== "page" && k !== "sort");
  const label = (k: string, v: string) =>
    k === "q" ? `« ${v} »`
    : k === "gender" ? GENDER[v as keyof typeof GENDER] ?? v
    : k === "family" ? families?.find((f) => f.slug === v)?.name ?? v
    : k === "collection" ? collections?.find((c) => c.slug === v)?.name ?? v
    : k === "max_price" ? `≤ ${formatFCFA(Number(v))}`
    : k === "volume" ? `${v} ml`
    : "Disponible";
  const pageNo = Number(current.page ?? 1);
  const pages = Math.max(1, Math.ceil(page.total / page.page_size));
  const href = (p: Record<string, string>) => `${basePath}${Object.keys(p).length ? `?${qs(p)}` : ""}`;

  return (
    <div className="flex flex-col gap-5">
      <Form action={basePath} className="flex gap-2">
        <input
          name="q"
          defaultValue={current.q}
          placeholder="Nom, note (ambre, néroli…)"
          aria-label="Rechercher un parfum"
          className={inputClass}
          maxLength={80}
        />
        <button className={buttonClass("primary", "md")}>Chercher</button>
      </Form>

      <details className="border border-filet bg-white">
        <summary className="flex h-12 cursor-pointer items-center px-4 text-sm font-semibold">Filtres et tri</summary>
        <Form action={basePath} className="grid gap-4 border-t border-filet p-4 md:grid-cols-3">
          {current.q && <input type="hidden" name="q" value={current.q} />}
          <Select name="sort" label="Trier par" value={current.sort} options={Object.entries(SORTS)} />
          <Select name="gender" label="Genre" value={current.gender} options={Object.entries(GENDER).map(([k, v]) => [k, v])} empty="Tous" />
          <Select name="family" label="Famille olfactive" value={current.family} options={(families ?? []).map((f) => [f.slug, f.name])} empty="Toutes" />
          {!collection && (
            <Select name="collection" label="Collection" value={current.collection} options={(collections ?? []).map((c) => [c.slug, c.name])} empty="Toutes" />
          )}
          <Select name="max_price" label="Prix maximum" value={current.max_price} options={PRICES.map((p) => [String(p), formatFCFA(p)])} empty="Tous les prix" />
          <Select name="volume" label="Contenance" value={current.volume} options={VOLUMES.map((v) => [String(v), `${v} ml`])} empty="Toutes" />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" name="in_stock" value="true" defaultChecked={current.in_stock === "true"} className="h-5 w-5" />
            Disponibles uniquement
          </label>
          <button className={`${buttonClass("primary", "sm")} md:col-start-3`}>Appliquer</button>
        </Form>
      </details>

      <div className="flex flex-wrap items-center gap-2 text-sm" aria-live="polite">
        <span className="text-encre-douce">
          {page.total} parfum{page.total > 1 ? "s" : ""}
        </span>
        {active.map(([k, v]) => {
          const rest = { ...current };
          delete rest[k];
          delete rest.page;
          return (
            <Link key={k} href={href(rest)} className="inline-flex items-center gap-1 rounded-full bg-surface px-3 py-1.5 text-encre" aria-label={`Retirer le filtre ${label(k, v)}`}>
              {label(k, v)} <span aria-hidden>×</span>
            </Link>
          );
        })}
        {active.length > 0 && (
          <Link href={basePath} className="font-semibold underline underline-offset-4">
            Tout effacer
          </Link>
        )}
      </div>

      {page.items.length ? (
        <ProductGrid products={page.items} />
      ) : (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p>Aucun parfum ne correspond à ces critères.</p>
          <Link href={basePath} className={buttonClass("secondary", "sm")}>
            Réinitialiser les filtres
          </Link>
        </div>
      )}

      {pages > 1 && (
        <nav className="flex items-center justify-center gap-4 py-4 text-sm" aria-label="Pagination">
          {pageNo > 1 && <Link href={href({ ...current, page: String(pageNo - 1) })}>← Précédent</Link>}
          <span>
            Page {pageNo} sur {pages}
          </span>
          {pageNo < pages && <Link href={href({ ...current, page: String(pageNo + 1) })}>Suivant →</Link>}
        </nav>
      )}
    </div>
  );
}

function Select({ name, label, value, options, empty }: {
  name: string;
  label: string;
  value?: string;
  options: string[][];
  empty?: string;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-semibold">
      {label}
      <select name={name} defaultValue={value ?? ""} className={inputClass}>
        {empty && <option value="">{empty}</option>}
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}
