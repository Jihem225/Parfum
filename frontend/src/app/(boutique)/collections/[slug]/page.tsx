import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Catalogue } from "@/components/boutique/catalogue";
import { Loading } from "@/components/ui";
import { getPublic } from "@/lib/server-api";
import type { Collection } from "@/lib/types";

export async function generateMetadata({ params }: PageProps<"/collections/[slug]">): Promise<Metadata> {
  const c = await getPublic<Collection>(`/catalog/collections/${(await params).slug}`);
  return { title: c?.name ?? "Collection", description: c?.description ?? undefined };
}

async function Content({ params, searchParams }: PageProps<"/collections/[slug]">) {
  const { slug } = await params;
  const collection = await getPublic<Collection>(`/catalog/collections/${slug}`);
  if (!collection) notFound();
  return (
    <>
      <h1 className="font-display text-[32px]">{collection.name}</h1>
      {collection.description && <p className="mb-5 mt-2 max-w-2xl text-encre-douce">{collection.description}</p>}
      <Catalogue searchParams={searchParams} basePath={`/collections/${slug}`} collection={slug} />
    </>
  );
}

export default function CollectionPage(props: PageProps<"/collections/[slug]">) {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6">
      <Suspense fallback={<Loading />}>
        <Content {...props} />
      </Suspense>
    </div>
  );
}
