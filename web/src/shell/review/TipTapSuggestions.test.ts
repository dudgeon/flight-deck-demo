// @vitest-environment jsdom
// omnigent-slim: tracked changes round-trip through markdown, and Suggesting
// mode turns typing and deleting into the user's suggestions.
import { Editor } from "@tiptap/core";
import { TextSelection } from "@tiptap/pm/state";
import { expect, test } from "vitest";
import { createMarkdownDocumentExtensions } from "../markdownDocumentExtensions";
import {
  SuggestionDelete,
  SuggestionInsert,
  SuggestingMode,
  decideSuggestions,
  findSuggestions,
  setSuggesting,
} from "./TipTapSuggestions";

function make(md: string) {
  return new Editor({
    extensions: [
      ...createMarkdownDocumentExtensions("c", "a.md"),
      SuggestionInsert,
      SuggestionDelete,
      SuggestingMode,
    ],
    content: md,
    contentType: "markdown",
  });
}

test("reads and writes CriticMarkup with its author", () => {
  const e = make(
    "Alerts{++ over the limit++}{>>@risk-review 2026-11-21T12:40 fewer alerts<<}.\n\nShow a {~~code~>reason~~}{>>@mara-okafor<<}.",
  );
  expect(findSuggestions(e.state.doc).map((s) => [s.kind, s.by, s.text, s.note])).toEqual([
    ["insert", "risk-review", " over the limit", "fewer alerts"],
    ["delete", "mara-okafor", "code", null],
    ["insert", "mara-okafor", "reason", null],
  ]);
  const md = e.getMarkdown();
  expect(md).toContain("{++over the limit++}{>>@risk-review 2026-11-21T12:40 fewer alerts<<}");
  expect(md).toContain("{--code--}{>>@mara-okafor<<}{++reason++}{>>@mara-okafor<<}");
  expect(e.state.doc.childCount).toBe(2);
});

test("Suggesting mode tracks typing and deleting, and decisions apply them", () => {
  const e = make("Hello world here.");
  setSuggesting(e, true);
  e.view.dispatch(e.state.tr.setSelection(TextSelection.create(e.state.doc, 12)));
  for (let i = 0; i < 3; i++) {
    const h = e.state.selection.head;
    e.view.dispatch(e.state.tr.delete(h - 1, h));
  }
  expect(e.getMarkdown()).toMatch(/^Hello wo\{--rld--\}\{>>@you [^<]+<<\} here\.$/);
  e.view.dispatch(e.state.tr.insertText("X"));
  // Deleting your own suggestion just removes it.
  const h = e.state.selection.head;
  e.view.dispatch(e.state.tr.delete(h - 1, h));
  expect(findSuggestions(e.state.doc).map((s) => s.kind)).toEqual(["delete"]);
  decideSuggestions(e, findSuggestions(e.state.doc), true);
  expect(e.getMarkdown()).toBe("Hello wo here.");
});

test("Suggesting mode refuses to join blocks", () => {
  const e = make("One two.\n\n## Head");
  setSuggesting(e, true);
  const before = e.state.doc.childCount;
  const pos = e.state.doc.child(0).nodeSize; // the boundary between the blocks
  e.view.dispatch(e.state.tr.delete(pos - 1, pos + 1));
  expect(e.state.doc.childCount).toBe(before);
  setSuggesting(e, false);
  e.view.dispatch(e.state.tr.delete(pos - 1, pos + 1));
  expect(e.state.doc.childCount).toBe(before - 1);
});
