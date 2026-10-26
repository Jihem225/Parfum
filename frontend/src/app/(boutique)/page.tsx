import Link from "next/link";
import { Suspense } from "react";
import { ProductCard, ProductGrid } from "@/components/boutique/product-card";
import { buttonClass, Loading } from "@/components/ui";
import { getPublic } from "@/lib/server-api";
import type { Collection, Family, Page, ProductCard as Card } from "@/lib/types";
import { tint } from "@/lib/format";

async function NewIn() {
  const page = await getPublic<Page<Card>>("/catalog/products?sort=nouveautes&page_size=8");
  if (!page?.items.length) return <p className="px-4 text-encre-douce">Les premiers parfums arrivent bientôt.</p>;
  return (
    <div className="flex gap-3 overflow-x-auto px-4 pb-2">
      {page.items.map((p, i) => (
        <div key={p.id} className="w-40 flex-none md:w-56">
          <ProductCard product={p} eager={i < 2} />
        </div>
      ))}
    </div>
  );
}

async function BestSellers() {
  const page = await getPublic<Page<Card>>("/catalog/products?sort=popularite&page_size=4");
  return page?.items.length ? <ProductGrid products={page.items} /> : null;
}

async function Collections() {
  const collections = (await getPublic<Collection[]>("/catalog/collections")) ?? [];
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {collections.map((c) => (
        <Link
          key={c.id}
          href={`/collections/${c.slug}`}
          className="flex h-24 flex-col justify-center gap-1 px-5 text-encre"
          style={{ background: tint(c.id + 2) }}
        >
          <span className="font-display text-[22px]">{c.name}</span>
          <span className="text-xs text-[#4a4038]">
            {c.product_count} parfum{c.product_count > 1 ? "s" : ""}
          </span>
        </Link>
      ))}
    </div>
  );
}

async function Families() {
  const families = (await getPublic<Family[]>("/catalog/families")) ?? [];
  return (
    <div className="flex flex-wrap gap-2">
      {families.map((f) => (
        <Link
          key={f.id}
          href={`/parfums?family=${f.slug}`}
          className="inline-flex h-11 items-center rounded-full border border-[#cfc8be] px-[18px] text-sm text-encre"
        >
          {f.name}
        </Link>
      ))}
    </div>
  );
}

function Section({ title, link, children }: { title: string; link?: string; children: React.ReactNode }) {
  return (
    <section className="mx-auto w-full max-w-6xl pt-8">
      <div className="flex items-baseline justify-between px-4 pb-4">
        <h2 className="font-display text-[26px]">{title}</h2>
        {link && (
          <Link href={link} className="text-[13px] font-semibold">
            Tout voir
          </Link>
        )}
      </div>
      <Suspense fallback={<Loading />}>{children}</Suspense>
    </section>
  );
}

export default function Home() {
  return (
    <>
      <section className="bg-[#ebdcc4] px-5 py-10 md:py-16">
        <div className="mx-auto flex max-w-6xl flex-col gap-4">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5c4a33]">Eaux de parfum</span>
          <h1 className="font-display text-[40px] leading-[1.08] md:text-6xl">
            Des sillages
            <br />
            nés à Abidjan
          </h1>
          <p className="max-w-md text-[15px] leading-relaxed text-[#3d342d]">
            Des eaux de parfum composées pour durer sous le soleil de la lagune.
          </p>
          <div className="flex flex-col gap-2.5 md:flex-row">
            <Link href="/parfums" className={buttonClass()}>
              Découvrir les parfums
            </Link>
            <Link href="/collections" className={buttonClass("ghost")}>
              Voir les collections
            </Link>
          </div>
        </div>
      </section>
      <section className="grid grid-cols-3 gap-2 border-b border-filet px-4 py-5 text-center text-xs leading-snug">
        <span>
          Paiement
          <br />à la livraison
        </span>
        <span>
          Livraison
          <br />à Abidjan
        </span>
        <span>
          Confirmé
          <br />
          par téléphone
        </span>
      </section>
      <Section title="Nouveautés" link="/parfums?sort=nouveautes">
        <NewIn />
      </Section>
      <Section title="Collections" link="/collections">
        <div className="px-4">
          <Collections />
        </div>
      </Section>
      <Section title="Meilleures ventes" link="/parfums?sort=popularite">
        <div className="px-4">
          <BestSellers />
        </div>
      </Section>
      <Section title="Trouver votre famille">
        <div className="px-4 pb-10">
          <Families />
        </div>
      </Section>
    </>
  );
}
