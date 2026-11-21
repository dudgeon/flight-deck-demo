// omnigent-slim: two highlight layers for the review panel, drawn as
// decorations so they never reach the saved markdown.
//
//  * Comment threads: the passage each thread quotes, yellow, darker when active.
//  * Fresh edits: text that changed on disk while the file was open (the
//    primary agent editing directly), tinted until the user marks it seen.

import { Extension } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";
import { Plugin, PluginKey, type EditorState } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { RefObject } from "react";
import type { ReviewThread } from "./reviewModel";

export interface ThreadHighlightState {
  threads: ReviewThread[];
  activeId: string | null;
  onClick: (threadId: string) => void;
}

export const threadHighlightKey = new PluginKey<DecorationSet>("reviewThreads");
export const freshEditsKey = new PluginKey<DecorationSet>("reviewFreshEdits");
const FRESH_SET = "omnigentFreshSet";

/** Where `quote` appears, as document positions; within one text block. */
export function findQuote(
  doc: PMNode,
  quote: string,
  occurrence = 1,
): { from: number; to: number } | null {
  const needle = quote.trim();
  if (!needle) return null;
  let seen = 0;
  let found: { from: number; to: number } | null = null;
  doc.descendants((node, pos) => {
    if (found) return false;
    if (!node.isTextblock) return true;
    // Map character offsets in the block's text back to positions.
    const offsets: number[] = [];
    let text = "";
    node.descendants((child, childPos) => {
      if (child.isText) {
        for (let i = 0; i < child.text!.length; i++) offsets.push(pos + 1 + childPos + i);
        text += child.text;
      }
    });
    let at = text.indexOf(needle);
    while (at !== -1) {
      seen += 1;
      if (seen === occurrence) {
        found = { from: offsets[at], to: offsets[at + needle.length - 1] + 1 };
        return false;
      }
      at = text.indexOf(needle, at + 1);
    }
    return false;
  });
  return found;
}

function threadDecorations(
  state: EditorState,
  highlight: ThreadHighlightState | null,
): DecorationSet {
  if (!highlight) return DecorationSet.empty;
  const decos: Decoration[] = [];
  for (const thread of highlight.threads) {
    if (thread.resolved) continue;
    const range = findQuote(state.doc, thread.anchor.quote, thread.anchor.occurrence ?? 1);
    if (!range) continue;
    decos.push(
      Decoration.inline(range.from, range.to, {
        class:
          thread.id === highlight.activeId
            ? "md-review-thread md-review-thread-active"
            : "md-review-thread",
        "data-thread-id": thread.id,
      }),
    );
  }
  return DecorationSet.create(state.doc, decos);
}

/** Ask the thread layer to redraw after its state ref changed. */
export function redrawThreads(view: { state: EditorState; dispatch: (tr: never) => void }): void {
  view.dispatch(
    view.state.tr.setMeta(threadHighlightKey, "rebuild").setMeta("addToHistory", false) as never,
  );
}

/** Changed ranges between two versions of a document, block by block. */
export function changedRanges(previous: PMNode, next: PMNode): { from: number; to: number }[] {
  const before = new Map<string, number>();
  previous.descendants((node) => {
    if (node.isTextblock) {
      before.set(node.textContent, (before.get(node.textContent) ?? 0) + 1);
      return false;
    }
    return true;
  });
  const oldBlocks: string[] = [];
  previous.descendants((node) => {
    if (node.isTextblock) {
      oldBlocks.push(node.textContent);
      return false;
    }
    return true;
  });
  const ranges: { from: number; to: number }[] = [];
  let index = 0;
  next.descendants((node, pos) => {
    if (!node.isTextblock) return true;
    const text = node.textContent;
    const i = index++;
    const left = before.get(text) ?? 0;
    if (left > 0) {
      before.set(text, left - 1);
      return false;
    }
    if (!text.trim()) return false;
    // Closest old block: the one at the same place, if any; mark only what differs.
    const old = oldBlocks[i] ?? "";
    let start = 0;
    while (start < text.length && start < old.length && text[start] === old[start]) start++;
    let end = 0;
    while (
      end < text.length - start &&
      end < old.length - start &&
      text[text.length - 1 - end] === old[old.length - 1 - end]
    )
      end++;
    // A block that shares little with the old one is new as a whole.
    if (text.length - start - end < 1) return false;
    if (start + end < text.length * 0.3) {
      start = 0;
      end = 0;
    }
    const offsets: number[] = [];
    node.descendants((child, childPos) => {
      if (child.isText)
        for (let k = 0; k < child.text!.length; k++) offsets.push(pos + 1 + childPos + k);
    });
    const from = offsets[start];
    const to = offsets[text.length - end - 1];
    if (from !== undefined && to !== undefined) ranges.push({ from, to: to + 1 });
    return false;
  });
  return ranges;
}

/** Tint what changed between `previous` and the editor's current document. */
export function markFreshEdits(
  view: { state: EditorState; dispatch: (tr: never) => void },
  previous: PMNode,
): number {
  const ranges = changedRanges(previous, view.state.doc);
  if (!ranges.length) return 0;
  view.dispatch(
    view.state.tr.setMeta(FRESH_SET, { add: ranges }).setMeta("addToHistory", false) as never,
  );
  return ranges.length;
}

export function clearFreshEdits(view: { state: EditorState; dispatch: (tr: never) => void }): void {
  view.dispatch(
    view.state.tr.setMeta(FRESH_SET, { clear: true }).setMeta("addToHistory", false) as never,
  );
}

export function freshEditCount(state: EditorState): number {
  return freshEditsKey.getState(state)?.find().length ?? 0;
}

export function createReviewDecorations(highlightRef: RefObject<ThreadHighlightState | null>) {
  return Extension.create({
    name: "reviewDecorations",
    addProseMirrorPlugins() {
      return [
        new Plugin<DecorationSet>({
          key: threadHighlightKey,
          state: {
            init: (_, state) => threadDecorations(state, highlightRef.current),
            apply: (tr, set, _old, state) =>
              tr.getMeta(threadHighlightKey) === "rebuild" || tr.docChanged
                ? threadDecorations(state, highlightRef.current)
                : set,
          },
          props: {
            decorations: (state) => threadHighlightKey.getState(state),
            handleClick: (_view, _pos, event) => {
              const el = (event.target as HTMLElement | null)?.closest?.("[data-thread-id]");
              const id = el?.getAttribute("data-thread-id");
              if (id) highlightRef.current?.onClick(id);
              return false;
            },
          },
        }),
        new Plugin<DecorationSet>({
          key: freshEditsKey,
          state: {
            init: () => DecorationSet.empty,
            apply: (tr, set) => {
              const meta = tr.getMeta(FRESH_SET) as
                { add?: { from: number; to: number }[]; clear?: boolean } | undefined;
              if (meta?.clear) return DecorationSet.empty;
              let next = set.map(tr.mapping, tr.doc);
              if (meta?.add) {
                next = next.add(
                  tr.doc,
                  meta.add.map((r) =>
                    Decoration.inline(r.from, r.to, { class: "md-review-fresh" }),
                  ),
                );
              }
              return next;
            },
          },
          props: { decorations: (state) => freshEditsKey.getState(state) },
        }),
      ];
    },
  });
}
