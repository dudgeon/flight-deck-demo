import { describe, expect, it } from "vitest";
import { hangarPath, participantSlug, unwrap } from "./hangarApi";

describe("hangar helpers", () => {
  it("maps a chat turn's name to the roster id", () => {
    expect(participantSlug("Mara Okafor")).toBe("mara-okafor");
    expect(participantSlug("  Risk Review! ")).toBe("risk-review");
  });

  it("builds Hangar paths with escaped ids", () => {
    expect(hangarPath.view("document-review", "who")).toBe("/hangar/views/document-review/who");
    expect(hangarPath.template("a b")).toBe("/hangar/views/template/a%20b");
  });

  it("reflows wrapped prose but keeps structure", () => {
    const text = [
      "You are standing in for Mara,",
      "the design lead.",
      "",
      "- The moment of a decline.",
      "  more about it",
      "**You:** hello",
      "[widget who]",
      "next line",
    ].join("\n");
    expect(unwrap(text)).toBe(
      [
        "You are standing in for Mara, the design lead.",
        "",
        "- The moment of a decline. more about it",
        "**You:** hello",
        "[widget who] next line",
      ].join("\n"),
    );
  });
});
