import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Loading } from "@/components/ui";
import { tint } from "@/lib/format";
import { getPublic } from "@/lib/server-api";
import type { Collection } from "@/lib/types";

export const metadata: Metadata = { title: "Collections" };

async function List() {
  const collections = (await getPublic<Collection[]>("/catalog/collections")) ?? [];
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {collections.map((c) => (
        <Link key={c.id} href={`/collections/${c.slug}`} className="flex min-h-28 flex-col justify-center gap-1 px-5 py-4 text-encre" style={{ background: tint(c.id + 2) }}>
          <span className="font-display text-2xl">{c.name}</span>
          {c.description && <span className="text-sm text-[#4a4038]">{c.description}</span>}
          <span className="text-xs text-[#4a4038]">
            {c.product_count} parfum{c.product_count > 1 ? "s" : ""}
          </span>
        </Link>
      ))}
    </div>
  );
}

export default function CollectionsPage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6">
      <h1 className="mb-5 font-display text-[32px]">Collections</h1>
      <Suspense fallback={<Loading />}>
        <List />
      </Suspense>
    </div>
  );
}
