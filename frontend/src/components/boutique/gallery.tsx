"use client";

import { useState } from "react";
import type { Image } from "@/lib/types";
import { ProductImage } from "../product-image";

export function Gallery({ images, productId, name }: { images: Image[]; productId: number; name: string }) {
  const [index, setIndex] = useState(0);
  return (
    <div className="flex flex-col gap-2">
      <ProductImage image={images[index] ?? null} productId={productId} name={name} eager className="aspect-[4/5] md:aspect-square" />
      {images.length > 1 && (
        <div className="flex gap-2 px-4 md:px-0">
          {images.map((img, i) => (
            <button
              key={img.id}
              type="button"
              aria-label={`Image ${i + 1} sur ${images.length}`}
              aria-pressed={i === index}
              onClick={() => setIndex(i)}
              className={`h-14 w-14 overflow-hidden border ${i === index ? "border-2 border-encre" : "border-filet"}`}
            >
              <ProductImage image={img} productId={productId} name={name} className="h-full w-full" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
