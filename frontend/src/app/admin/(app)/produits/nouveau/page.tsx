"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ProductForm, type ProductFields } from "@/components/admin/product-form";
import { AdminTitle, Card } from "@/components/admin/ui";
import { Alert } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import type { AdminProduct } from "@/lib/types";

export default function NouveauProduitPage() {
  const router = useRouter();
  const create = useMutation({
    mutationFn: (v: ProductFields) => api<AdminProduct>("/admin/products", { json: v }),
    onSuccess: (p) => router.push(`/admin/produits/${p.id}`),
  });
  return (
    <>
      <AdminTitle>Nouveau parfum</AdminTitle>
      <p className="text-sm text-encre-douce">Le parfum est créé en brouillon. Ajoutez ensuite ses contenances et ses images, puis publiez-le.</p>
      {create.isError && <Alert>{errorMessage(create.error)}</Alert>}
      <Card><ProductForm onSubmit={(v) => create.mutate(v)} pending={create.isPending} submitLabel="Créer le brouillon" /></Card>
    </>
  );
}
