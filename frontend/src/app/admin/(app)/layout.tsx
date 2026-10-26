import type { Metadata } from "next";
import { Suspense } from "react";
import { AdminShell } from "@/components/admin/admin-shell";
import { Loading } from "@/components/ui";

export const metadata: Metadata = { title: "Administration", robots: { index: false } };

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<Loading />}>
      <AdminShell>{children}</AdminShell>
    </Suspense>
  );
}
