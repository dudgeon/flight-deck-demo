// omnigent-slim: tracked changes ("suggestions") for the markdown editor.
//
// A suggestion is stored in the file as CriticMarkup followed by a CriticMarkup
// comment naming its author, which `pa review` (skills/view-kit/scripts/
// docreview.py) reads and writes too:
//
//   {++added++}{>>@risk-review 2026-11-21T12:40 why<<}
//   {--removed--}{>>@you<<}
//   {~~old~>new~~}{>>@mara-okafor<<}     (read as a removal then an addition)
//
// In the editor they are two marks, `suggestionInsert` and `suggestionDelete`,
// with the author in `by`. In Suggesting mode a plugin turns the user's typing
// into insertions and their deletions into struck-through text, both by "you".

import { type Editor, Extension, Mark, type JSONContent } from "@tiptap/core";
import type { Mark as PMMark, MarkType, Node as PMNode, Slice } from "@tiptap/pm/model";
import { Plugin, PluginKey, TextSelection, type Transaction } from "@tiptap/pm/state";
import { ReplaceStep } from "@tiptap/pm/transform";

export const INSERT_MARK = "suggestionInsert";
export const DELETE_MARK = "suggestionDelete";
/** The author id for the person using the editor, as in the sidecar file. */
export const USER_ID = "you";

/** One change and its author: `{++x++}`, `{--x--}` or `{~~x~>y~~}`, then `{>>meta<<}`. */
const CHANGE =
  /^(?:\{\+\+([\s\S]*?)\+\+\}|\{--([\s\S]*?)--\}|\{~~([\s\S]*?)~>([\s\S]*?)~~\})(?:\{>>([\s\S]*?)<<\})?/;

export interface SuggestionAttrs {
  by: string | null;
  at: string | null;
  note: string | null;
}

/** Read `@id 2026-11-21T12:40 a note` from a CriticMarkup comment. */
export function parseMeta(meta: string | undefined): SuggestionAttrs {
  const attrs: SuggestionAttrs = { by: null, at: null, note: null };
  if (!meta) return attrs;
  const words = meta.trim().split(/\s+/);
  if (words[0]?.startsWith("@")) {
    attrs.by = words.shift()!.slice(1) || null;
    if (words[0] && /^\d{4}-\d\d-\d\d/.test(words[0])) attrs.at = words.shift()!;
  }
  attrs.note = words.join(" ") || null;
  return attrs;
}

/** The `{>>...<<}` that follows a change, or nothing when no attribute is set. */
export function renderMeta(attrs: Partial<SuggestionAttrs>): string {
  const parts = [attrs.by ? `@${attrs.by}` : "", attrs.at ?? "", attrs.note ?? ""].filter(Boolean);
  return parts.length ? `{>>${parts.join(" ")}<<}` : "";
}

function nowStamp(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function withMark(nodes: JSONContent[], type: string, attrs: SuggestionAttrs): JSONContent[] {
  return nodes.map((node) =>
    node.type === "text"
      ? { ...node, marks: [...(node.marks ?? []), { type, attrs: { ...attrs } }] }
      : node,
  );
}

const sharedAttributes = () => ({
  by: { default: null, renderHTML: (a: SuggestionAttrs) => (a.by ? { "data-by": a.by } : {}) },
  at: { default: null, renderHTML: () => ({}) },
  note: { default: null, renderHTML: (a: SuggestionAttrs) => (a.note ? { title: a.note } : {}) },
});

/** Added text. Its tokenizer also reads removals and replacements, so all three parse in one place. */
export const SuggestionInsert = Mark.create({
  name: INSERT_MARK,
  inclusive: false,
  excludes: DELETE_MARK,
  addAttributes: sharedAttributes,
  parseHTML: () => [{ tag: "ins[data-suggestion]" }],
  renderHTML: ({ HTMLAttributes }) => [
    "ins",
    { ...HTMLAttributes, "data-suggestion": "", class: "md-suggestion md-suggestion-insert" },
    0,
  ],

  markdownTokenizer: {
    name: "criticChange",
    level: "inline",
    start: (source: string) => {
      const hit = source.search(/\{(?:\+\+|--|~~)/);
      return hit;
    },
    tokenize(source, _tokens, helpers) {
      const match = CHANGE.exec(source);
      if (!match) return undefined;
      const [raw, ins, del, oldText, newText, meta] = match;
      const parts: { kind: string; tokens: unknown[] }[] = [];
      if (ins !== undefined) parts.push({ kind: INSERT_MARK, tokens: helpers.inlineTokens(ins) });
      else if (del !== undefined)
        parts.push({ kind: DELETE_MARK, tokens: helpers.inlineTokens(del) });
      else {
        parts.push({ kind: DELETE_MARK, tokens: helpers.inlineTokens(oldText ?? "") });
        parts.push({ kind: INSERT_MARK, tokens: helpers.inlineTokens(newText ?? "") });
      }
      return { type: "criticChange", raw, parts, meta };
    },
  },
  markdownTokenName: "criticChange",
  parseMarkdown: (token, helpers) => {
    const attrs = parseMeta(token.meta as string | undefined);
    const parts = (token.parts ?? []) as { kind: string; tokens: never[] }[];
    return parts.flatMap((part) => withMark(helpers.parseInline(part.tokens), part.kind, attrs));
  },
  renderMarkdown: (node, helpers) =>
    `{++${helpers.renderChildren(node)}++}${renderMeta(node.attrs ?? {})}`,
});

/** Removed text: shown struck through until someone accepts or rejects it. */
export const SuggestionDelete = Mark.create({
  name: DELETE_MARK,
  inclusive: false,
  excludes: INSERT_MARK,
  addAttributes: sharedAttributes,
  parseHTML: () => [{ tag: "del[data-suggestion]" }],
  renderHTML: ({ HTMLAttributes }) => [
    "del",
    { ...HTMLAttributes, "data-suggestion": "", class: "md-suggestion md-suggestion-delete" },
    0,
  ],
  renderMarkdown: (node, helpers) =>
    `{--${helpers.renderChildren(node)}--}${renderMeta(node.attrs ?? {})}`,
});

// ---------------------------------------------------------------------------
// Finding suggestions, accepting and rejecting them
// ---------------------------------------------------------------------------

export interface SuggestionRange {
  key: string;
  kind: "insert" | "delete";
  from: number;
  to: number;
  by: string | null;
  at: string | null;
  note: string | null;
  text: string;
}

function suggestionMark(node: PMNode): PMMark | undefined {
  return node.marks.find((m) => m.type.name === INSERT_MARK || m.type.name === DELETE_MARK);
}

/** Every run of suggested text in document order. Adjacent runs with the same author merge. */
export function findSuggestions(doc: PMNode): SuggestionRange[] {
  const out: SuggestionRange[] = [];
  doc.descendants((node, pos) => {
    if (!node.isText) return;
    const mark = suggestionMark(node);
    if (!mark) return;
    const kind = mark.type.name === INSERT_MARK ? "insert" : "delete";
    const last = out[out.length - 1];
    const attrs = mark.attrs as SuggestionAttrs;
    if (
      last &&
      last.kind === kind &&
      last.to === pos &&
      last.by === attrs.by &&
      last.at === attrs.at
    ) {
      last.to = pos + node.nodeSize;
      last.text += node.text ?? "";
      return;
    }
    out.push({
      key: `${kind}:${pos}`,
      kind,
      from: pos,
      to: pos + node.nodeSize,
      by: attrs.by,
      at: attrs.at,
      note: attrs.note,
      text: node.text ?? "",
    });
  });
  return out;
}

/**
 * Accept or reject suggestions. Accepting an addition keeps the text, accepting
 * a removal deletes it; rejecting does the opposite. Runs in one transaction,
 * last first, so earlier positions stay valid.
 */
export function decideSuggestions(
  editor: Editor,
  ranges: SuggestionRange[],
  accept: boolean,
): void {
  const { state } = editor;
  const tr = state.tr.setMeta(SUGGEST_SKIP, true);
  for (const range of [...ranges].sort((a, b) => b.from - a.from)) {
    const keep = (range.kind === "insert") === accept;
    if (keep)
      tr.removeMark(
        range.from,
        range.to,
        state.schema.marks[range.kind === "insert" ? INSERT_MARK : DELETE_MARK],
      );
    else tr.delete(range.from, range.to);
  }
  // A focused editor marks the change as the user's, so it autosaves.
  editor.view.focus();
  editor.view.dispatch(tr);
}

// ---------------------------------------------------------------------------
// Suggesting mode
// ---------------------------------------------------------------------------

/** Set on transactions the suggesting plugin must leave alone. */
export const SUGGEST_SKIP = "omnigentSuggestSkip";
export const suggestingKey = new PluginKey<boolean>("suggesting");

/** Turn Suggesting mode on or off. */
export function setSuggesting(editor: Editor, on: boolean): void {
  editor.view.dispatch(editor.state.tr.setMeta(suggestingKey, on).setMeta(SUGGEST_SKIP, true));
}

export function isSuggesting(editor: Editor | null): boolean {
  return !!editor && suggestingKey.getState(editor.state) === true;
}

function hasMarkOf(node: PMNode, type: MarkType, by?: string): boolean {
  return node.marks.some((m) => m.type === type && (by === undefined || m.attrs.by === by));
}

/** Rewrite one user transaction so it suggests instead of edits. */
function trackTransaction(tr: Transaction, out: Transaction, oldHead: number): Transaction | null {
  const schema = out.doc.type.schema;
  const insType = schema.marks[INSERT_MARK];
  const delType = schema.marks[DELETE_MARK];
  const attrs = { by: USER_ID, at: nowStamp(), note: null };
  let cursor: number | null = null;

  tr.steps.forEach((step, index) => {
    if (!(step instanceof ReplaceStep)) return;
    const before = tr.docs[index];
    const { from, to } = step as unknown as { from: number; to: number };
    const slice = (step as unknown as { slice: Slice }).slice;
    const rest = tr.mapping.slice(index + 1);
    const start = out.mapping.map(rest.map(from, -1), -1);
    const end = out.mapping.map(rest.map(from + slice.size, 1), 1);

    // Typed or pasted text becomes the user's addition.
    if (slice.size > 0 && end > start) {
      out.removeMark(start, end, delType);
      out.addMark(start, end, insType.create(attrs));
      cursor = end;
    }

    // Removed text comes back, struck through, unless it was the user's own addition.
    if (to > from) {
      const removed = before.slice(from, to);
      let texts = 0;
      let own = 0;
      before.nodesBetween(from, to, (node) => {
        if (!node.isText) return;
        texts += 1;
        if (hasMarkOf(node, insType, USER_ID)) own += 1;
      });
      if (texts > 0 && own === texts) return;
      const insertedAt = start;
      out.replace(insertedAt, insertedAt, removed);
      const span = removed.size;
      // Strike through what came back; drop the user's own additions inside it.
      const ownRanges: [number, number][] = [];
      out.doc.nodesBetween(insertedAt, insertedAt + span, (node, pos) => {
        if (!node.isText) return;
        const a = Math.max(pos, insertedAt);
        const b = Math.min(pos + node.nodeSize, insertedAt + span);
        if (hasMarkOf(node, insType, USER_ID)) ownRanges.push([a, b]);
        else if (!hasMarkOf(node, delType)) out.addMark(a, b, delType.create(attrs));
      });
      for (const [a, b] of ownRanges.reverse()) out.delete(a, b);
      const removedOwn = ownRanges.reduce((n, [a, b]) => n + (b - a), 0);
      // Backspace leaves the caret before the struck text; Delete leaves it after.
      const backspace = oldHead === to;
      cursor = backspace ? insertedAt : insertedAt + span - removedOwn;
      if (slice.size > 0) cursor = out.mapping.map(end, 1);
    }
  });

  if (!out.docChanged) return null;
  if (cursor !== null) {
    const pos = Math.max(0, Math.min(cursor, out.doc.content.size));
    out.setSelection(TextSelection.near(out.doc.resolve(pos), -1));
  }
  return out.setMeta(SUGGEST_SKIP, true);
}

/** The Suggesting-mode plugin. Off until `setSuggesting(editor, true)`. */
export const SuggestingMode = Extension.create({
  name: "suggestingMode",
  addProseMirrorPlugins() {
    return [
      new Plugin<boolean>({
        key: suggestingKey,
        state: {
          init: () => false,
          apply: (tr, value) => {
            const next = tr.getMeta(suggestingKey);
            return typeof next === "boolean" ? next : value;
          },
        },
        // Block structure is not tracked, so in Suggesting mode a deletion that
        // would join or remove blocks (Backspace at the start of a paragraph,
        // a selection across paragraphs) is refused rather than made silently.
        filterTransaction(tr, state) {
          if (
            suggestingKey.getState(state) !== true ||
            tr.getMeta(SUGGEST_SKIP) ||
            tr.getMeta("addToHistory") === false
          )
            return true;
          return !tr.steps.some((step, index) => {
            if (!(step instanceof ReplaceStep)) return false;
            const { from, to } = step as unknown as { from: number; to: number };
            if (to <= from) return false;
            const doc = tr.docs[index];
            return doc.resolve(from).parent !== doc.resolve(to).parent;
          });
        },
        appendTransaction(transactions, oldState, newState) {
          if (suggestingKey.getState(newState) !== true) return null;
          const user = transactions.filter(
            (tr) =>
              tr.docChanged &&
              !tr.getMeta(SUGGEST_SKIP) &&
              tr.getMeta("addToHistory") !== false &&
              !tr.getMeta("history$"),
          );
          if (user.length !== 1 || transactions.length !== 1) return null;
          return trackTransaction(user[0], newState.tr, oldState.selection.head);
        },
      }),
    ];
  },
});
