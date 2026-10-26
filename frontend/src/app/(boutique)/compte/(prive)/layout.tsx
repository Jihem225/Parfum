import { Suspense } from "react";
import { CompteShell } from "@/components/compte/compte-shell";
import { Loading } from "@/components/ui";

export default function CompteLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<Loading />}>
      <CompteShell>{children}</CompteShell>
    </Suspense>
  );
}
