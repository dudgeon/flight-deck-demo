import { describe, expect, it } from "vitest";
import { noteBlocks, parseDirectorNotes } from "./directorNotes";

describe("parseDirectorNotes", () => {
  it("reads both notes and whether a director has written anything", () => {
    const notes = parseDirectorNotes({
      exists: true,
      state: { file: "director/state.md", text: "# T\n", updated: 1700000000.5 },
      memory: { file: "director/memory.md", text: "", updated: null },
    });
    expect(notes.exists).toBe(true);
    expect(notes.state.updated).toBe(1700000000.5);
    expect(notes.memory).toEqual({ file: "director/memory.md", text: "", updated: null });
  });

  it("treats a missing or odd answer as no notes", () => {
    const notes = parseDirectorNotes(null);
    expect(notes.exists).toBe(false);
    expect(notes.state.text).toBe("");
  });
});

describe("noteBlocks", () => {
  it("drops the title and empty sections, keeps headings with content, items and paragraphs", () => {
    const text = [
      "# Where the project stands",
      "",
      "Rewritten whole at each checkpoint.",
      "",
      "## Working on now",
      "- Shaping release dates (thread open)",
      "",
      "## Waiting on the person",
      "",
      "## Decided here",
      "Strictness by the book",
      "for this intent.",
      "",
      "## Next",
      "",
    ].join("\n");
    expect(noteBlocks(text)).toEqual([
      { kind: "para", text: "Rewritten whole at each checkpoint." },
      { kind: "heading", text: "Working on now" },
      { kind: "item", text: "Shaping release dates (thread open)" },
      { kind: "heading", text: "Decided here" },
      { kind: "para", text: "Strictness by the book for this intent." },
    ]);
  });
});
