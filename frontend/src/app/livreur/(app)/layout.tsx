import type { Metadata } from "next";
import { Suspense } from "react";
import { LivreurShell } from "@/components/livreur/livreur-shell";
import { Loading } from "@/components/ui";

export const metadata: Metadata = { title: "Livraisons", robots: { index: false } };

export default function LivreurLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<Loading />}>
      <LivreurShell>{children}</LivreurShell>
    </Suspense>
  );
}
