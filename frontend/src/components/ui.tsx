import type { ButtonHTMLAttributes, ReactNode } from "react";
import { ORDER_STATUS } from "@/lib/format";
import type { OrderStatus } from "@/lib/types";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-encre text-porcelaine hover:bg-[#3a322c]",
  secondary: "border border-[#cfc8be] bg-white text-encre hover:border-encre",
  ghost: "text-encre underline-offset-4 hover:underline",
  danger: "bg-erreur text-white hover:bg-[#5e2117]",
};

/** Classes d'un bouton (utilisables aussi sur un <Link>). Cible tactile ≥ 44 px. */
export function buttonClass(variant: Variant = "primary", size: "md" | "sm" = "md"): string {
  const height = size === "md" ? "h-[52px] px-6 text-[15px]" : "h-10 px-4 text-sm";
  return `inline-flex items-center justify-center gap-2 rounded-[2px] font-semibold tracking-[0.02em] transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${height} ${VARIANTS[variant]}`;
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "md" | "sm" }) {
  return <button type={type} className={`${buttonClass(variant, size)} ${className}`} {...props} />;
}

export const inputClass =
  "h-12 w-full rounded-[2px] border border-[#cfc8be] bg-white px-3 text-[15px] text-encre outline-none focus:border-encre aria-[invalid=true]:border-erreur";

export function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="font-semibold">{label}</span>
      {children}
      {hint && !error && <span className="text-encre-douce">{hint}</span>}
      {error && (
        <span role="alert" className="text-erreur">
          {error}
        </span>
      )}
    </label>
  );
}

export function Alert({ tone = "error", children }: { tone?: "error" | "success" | "info"; children: ReactNode }) {
  const tones = {
    error: "border-erreur text-erreur bg-[#f8ecea]",
    success: "border-succes text-succes bg-[#eaf2ee]",
    info: "border-info text-info bg-[#eaeff6]",
  };
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`border-l-4 px-4 py-3 text-sm ${tones[tone]}`}>
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-encre-douce">{children}</span>;
}

const STATUS_TONE: Partial<Record<OrderStatus, string>> = {
  EN_ATTENTE_CONFIRMATION: "bg-encre text-porcelaine",
  LIVREE: "bg-succes text-white",
  ECHEC_LIVRAISON: "bg-safran text-white",
  ANNULEE: "bg-[#e2ddd5] text-encre",
  RETOURNEE: "bg-[#e2ddd5] text-encre",
};

export function StatusPill({ status }: { status: OrderStatus }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_TONE[status] ?? "bg-surface text-encre"}`}>
      {ORDER_STATUS[status]}
    </span>
  );
}

export function Loading({ label = "Chargement…" }: { label?: string }) {
  return (
    <p role="status" className="py-8 text-center text-encre-douce">
      {label}
    </p>
  );
}
