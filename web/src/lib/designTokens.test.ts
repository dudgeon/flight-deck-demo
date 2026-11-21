// omnigent-slim: the canvas viewer hands every artifact the current design tokens.
import { describe, expect, it } from "vitest";
import { injectDesignTokens } from "./artifactBridge";
import { PA_TOKENS } from "./designTokens.generated";

describe("injectDesignTokens", () => {
  const page =
    "<!doctype html><html><head><style>:root{--pa-navy:#123}</style></head><body>x</body></html>";

  it("adds the current mode's tokens after the artifact's own styles", () => {
    const out = injectDesignTokens(page, "dark");
    const own = out.indexOf("--pa-navy:#123");
    const injected = out.indexOf("data-pa-tokens");
    expect(injected).toBeGreaterThan(own);
    expect(injected).toBeLessThan(out.indexOf("</head>"));
    expect(out).toContain(`--pa-navy:${PA_TOKENS.dark.navy}`);
    expect(out).toContain("color-scheme:dark");
    expect(out).toContain('setAttribute("data-theme","dark")');
  });

  it("uses light values and base tokens in light mode", () => {
    const out = injectDesignTokens(page, "light");
    expect(out).toContain(`--pa-navy:${PA_TOKENS.light.navy}`);
    expect(out).toContain(`--pa-r:${PA_TOKENS.base.r}`);
  });

  it("appends to a fragment with no head", () => {
    expect(
      injectDesignTokens("<p>hi</p>", "light").startsWith("<p>hi</p><style data-pa-tokens>"),
    ).toBe(true);
  });
});
