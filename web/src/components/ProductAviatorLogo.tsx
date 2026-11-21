// omnigent-slim: the Product Aviator logo, shown in place of Otto on the
// new-session screen. The SVG fills with currentColor, and its color comes
// from --brand-logo in index.css (navy in light mode, near-white in dark), so
// a later reskin only changes the brand tokens there.
import logoSvg from "@/assets/product-aviator-logo.svg?raw";

export function ProductAviatorLogo({ className }: { className?: string }) {
  return (
    <span
      role="img"
      aria-label="Product Aviator"
      className={`inline-block aspect-[1698/654] text-[var(--brand-logo)] [&>svg]:h-full [&>svg]:w-full ${className ?? ""}`}
      // Bundled at build time from a local file; no network load.
      dangerouslySetInnerHTML={{ __html: logoSvg }}
    />
  );
}
