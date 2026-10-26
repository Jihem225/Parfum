import { tint } from "@/lib/format";
import type { Image } from "@/lib/types";

/** Visuel produit sur fond teinté. Les images sont déjà en WebP ≤ 2000 px (backend), servies
 * telles quelles : <img> fonctionne aussi bien avec /media (dév) qu'avec R2 (production). */
export function ProductImage({
  image,
  productId,
  name,
  className = "",
  eager = false,
}: {
  image: Image | null;
  productId: number;
  name: string;
  className?: string;
  eager?: boolean;
}) {
  return (
    <div className={`flex items-center justify-center overflow-hidden ${className}`} style={{ background: tint(productId) }}>
      {image ? (
        // eslint-disable-next-line @next/next/no-img-element -- voir commentaire ci-dessus
        <img
          src={image.url}
          alt={image.alt_text || name}
          loading={eager ? "eager" : "lazy"}
          className="h-full w-full object-contain"
        />
      ) : (
        <span className="font-display text-4xl text-encre/30" aria-hidden>
          {name.charAt(0)}
        </span>
      )}
    </div>
  );
}
