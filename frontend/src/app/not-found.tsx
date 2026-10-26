import Link from "next/link";
import { buttonClass } from "@/components/ui";

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="font-display text-4xl">Page introuvable</h1>
      <p className="text-encre-douce">Cette page n&apos;existe pas ou n&apos;est plus disponible.</p>
      <Link href="/parfums" className={buttonClass()}>
        Voir les parfums
      </Link>
    </main>
  );
}
