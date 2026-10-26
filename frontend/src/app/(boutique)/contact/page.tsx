import type { Metadata } from "next";
import { Suspense } from "react";
import { formatPhone } from "@/lib/format";
import { getPublic } from "@/lib/server-api";
import type { ShopInfo } from "@/lib/types";
import { ContactForm } from "./contact-form";

export const metadata: Metadata = { title: "Contact" };

async function ShopDetails() {
  const shop = await getPublic<ShopInfo>("/shop").catch(() => null);
  if (!shop) return null;
  return (
    <ul className="flex flex-col gap-1 bg-surface p-4 text-sm">
      {shop.phone && <li>Téléphone : <a href={`tel:+225${shop.phone}`} className="font-semibold">{formatPhone(shop.phone)}</a></li>}
      {shop.whatsapp && <li>WhatsApp : <a href={`https://wa.me/225${shop.whatsapp}`} className="font-semibold">{formatPhone(shop.whatsapp)}</a></li>}
      {shop.email && <li>E-mail : <a href={`mailto:${shop.email}`} className="font-semibold">{shop.email}</a></li>}
      {shop.address && <li>{shop.address}</li>}
      {shop.opening_hours && <li>{shop.opening_hours}</li>}
    </ul>
  );
}

export default function ContactPage() {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 py-6">
      <h1 className="font-display text-[32px]">Contact</h1>
      <Suspense>
        <ShopDetails />
      </Suspense>
      <ContactForm />
    </div>
  );
}
