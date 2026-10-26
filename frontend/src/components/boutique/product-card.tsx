import Link from "next/link";
import { formatFCFA, GENDER, stockLabel } from "@/lib/format";
import type { ProductCard as Card } from "@/lib/types";
import { ProductImage } from "../product-image";

export function ProductCard({ product, eager = false }: { product: Card; eager?: boolean }) {
  const out = product.stock_status === "OUT";
  return (
    <Link href={`/parfums/${product.slug}`} className="group flex flex-col gap-2.5 text-encre">
      <div className="relative">
        <ProductImage image={product.image} productId={product.id} name={product.name} eager={eager} className="aspect-[4/5]" />
        {product.stock_status !== "IN_STOCK" && (
          // Badge opaque (pas de transparence) : contraste conforme, y compris en rupture.
          <span className={`absolute left-2.5 top-2.5 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${out ? "bg-encre text-porcelaine" : "bg-safran text-white"}`}>
            {stockLabel(product.stock_status, product.low_stock_count)}
          </span>
        )}
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="font-display text-[17px] group-hover:text-safran">{product.name}</span>
        <span className="text-xs text-encre-douce">
          {product.family.name} · {GENDER[product.gender]}
        </span>
        <span className="mt-0.5 text-[13px] font-semibold">dès {formatFCFA(product.min_price)}</span>
      </div>
    </Link>
  );
}

export function ProductGrid({ products }: { products: Card[] }) {
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-6 md:grid-cols-3 lg:grid-cols-4">
      {products.map((p, i) => (
        <ProductCard key={p.id} product={p} eager={i < 4} />
      ))}
    </div>
  );
}
