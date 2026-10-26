import type { Metadata } from "next";
import { Suspense } from "react";
import { Catalogue } from "@/components/boutique/catalogue";
import { Loading } from "@/components/ui";

export const metadata: Metadata = { title: "Parfums", description: "Toutes nos eaux de parfum, livrées à Abidjan." };

export default function ParfumsPage({ searchParams }: PageProps<"/parfums">) {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6">
      <h1 className="mb-5 font-display text-[32px]">Parfums</h1>
      <Suspense fallback={<Loading />}>
        <Catalogue searchParams={searchParams} basePath="/parfums" />
      </Suspense>
    </div>
  );
}
