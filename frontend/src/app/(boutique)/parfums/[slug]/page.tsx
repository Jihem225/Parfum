import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { AddToCart } from "@/components/boutique/add-to-cart";
import { Gallery } from "@/components/boutique/gallery";
import { ProductGrid } from "@/components/boutique/product-card";
import { Eyebrow, Loading } from "@/components/ui";
import { GENDER } from "@/lib/format";
import { getPublic } from "@/lib/server-api";
import type { ProductDetail } from "@/lib/types";

export async function generateMetadata({ params }: PageProps<"/parfums/[slug]">): Promise<Metadata> {
  const p = await getPublic<ProductDetail>(`/catalog/products/${(await params).slug}`);
  if (!p) return { title: "Parfum introuvable" };
  const image = p.images[0]?.url;
  return {
    title: p.name,
    description: p.description.slice(0, 160) || `${p.name}, eau de parfum ${p.family.name.toLowerCase()}.`,
    openGraph: image ? { images: [image] } : undefined,
  };
}

async function Product({ params }: { params: PageProps<"/parfums/[slug]">["params"] }) {
  const product = await getPublic<ProductDetail>(`/catalog/products/${(await params).slug}`);
  if (!product) notFound();
  const notes = [
    ["Tête", product.top_notes],
    ["Cœur", product.heart_notes],
    ["Fond", product.base_notes],
  ].filter(([, v]) => v);
  return (
    <>
      <div className="grid gap-6 md:grid-cols-2 md:gap-10">
        <Gallery images={product.images} productId={product.id} name={product.name} />
        <div className="flex flex-col gap-5 px-4 md:px-0">
          <div className="flex flex-col gap-1.5">
            <Eyebrow>Collection {product.collection.name}</Eyebrow>
            <h1 className="font-display text-[34px] leading-tight">{product.name}</h1>
            <span className="text-sm text-encre-douce">
              Eau de parfum · {product.family.name} · {GENDER[product.gender]}
            </span>
          </div>
          <AddToCart variants={product.variants} />
          <div className="flex flex-col gap-2.5 bg-surface p-3.5 text-[13px] leading-snug">
            <span>
              Vous payez <strong>en espèces à la livraison</strong>, après avoir reçu votre colis.
            </span>
            <span>Livraison à Abidjan ; frais et délai selon la commune, affichés avant de commander.</span>
          </div>
          {notes.length > 0 && (
            <section className="flex flex-col gap-3">
              <h2 className="font-display text-[22px]">Pyramide olfactive</h2>
              <dl className="border-t border-filet">
                {notes.map(([label, value]) => (
                  <div key={label} className="flex gap-4 border-b border-filet py-3">
                    <dt className="w-16 flex-none pt-0.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-encre-douce">{label}</dt>
                    <dd className="text-[15px]">{value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}
          {product.description && <p className="whitespace-pre-line text-[15px] leading-relaxed text-[#3d342d]">{product.description}</p>}
        </div>
      </div>
      {product.similar.length > 0 && (
        <section className="px-4 py-10 md:px-0">
          <h2 className="mb-4 font-display text-[22px]">Vous aimerez aussi</h2>
          <ProductGrid products={product.similar} />
        </section>
      )}
    </>
  );
}

export default function ProductPage({ params }: PageProps<"/parfums/[slug]">) {
  return (
    <div className="mx-auto w-full max-w-6xl md:px-4 md:py-8">
      <Suspense fallback={<Loading />}>
        <Product params={params} />
      </Suspense>
    </div>
  );
}
