import type { Metadata } from "next";
import { Bodoni_Moda, Manrope } from "next/font/google";
import { Providers } from "@/components/providers";
import "./globals.css";

const bodoni = Bodoni_Moda({ variable: "--font-bodoni", subsets: ["latin"] });
const manrope = Manrope({ variable: "--font-manrope", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Projet Parfums", template: "%s · Projet Parfums" },
  description: "Eaux de parfum livrées à Abidjan, paiement à la livraison.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr" className={`${bodoni.variable} ${manrope.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
