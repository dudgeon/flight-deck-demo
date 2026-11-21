// omnigent-slim: the Product Aviator brand mark at the top of the sidebar, in
// place of the Omnigent wordmark: the emblem (robot and wings, no lettering)
// followed by the name as real text, so it stays crisp and aligned at small
// sizes. The SVG fills with currentColor, and both take their color from
// --brand-logo in index.css (navy in light mode, near-white in dark), so a
// later reskin only changes the brand tokens there.
import emblemSvg from "@/assets/product-aviator-emblem.svg?raw";

export function ProductAviatorLogo({ className }: { className?: string }) {
  return (
    <span
      className={`flex items-center gap-2 text-[var(--brand-logo)] ${className ?? ""}`}
    >
      <span
        aria-hidden
        className="inline-block h-[18px] aspect-[1690/500] shrink-0 [&>svg]:block [&>svg]:h-full [&>svg]:w-full"
        // Bundled at build time from a local file; no network load.
        dangerouslySetInnerHTML={{ __html: emblemSvg }}
      />
      <span className="whitespace-nowrap text-[15px] font-semibold leading-none tracking-tight">
        Product Aviator
      </span>
    </span>
  );
}
