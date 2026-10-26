import { Footer } from "@/components/boutique/footer";
import { Header } from "@/components/boutique/header";

export default function BoutiqueLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <Header />
      <main className="flex flex-1 flex-col">{children}</main>
      <Footer />
    </>
  );
}
