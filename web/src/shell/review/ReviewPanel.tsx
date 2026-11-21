// omnigent-slim: the review panel beside the markdown editor. Comment threads
// (with @mentions that bring participants in), suggested changes to accept or
// reject, Suggesting mode, and the primary agent's fresh edits.
//
// Threads live in `<document>.review.json`; suggestions live in the markdown as
// CriticMarkup (see TipTapSuggestions.ts). Both are plain files, so agents use
// `pa review` to take part and this panel just reads and writes the same files.

import { useQuery } from "@tanstack/react-query";
import type { Editor } from "@tiptap/core";
import { Check, ChevronRight, MessageSquarePlus, RotateCcw, Trash2, X } from "lucide-react";
import { createPortal } from "react-dom";
import {
  type KeyboardEvent,
  type RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { ParticipantMark } from "@/components/chat/ParticipantTurn";
import { fetchFileContent, useFileContent } from "@/hooks/useFileContent";
import { useWriteFileContent } from "@/hooks/useWriteFileContent";
import { ARTIFACT_ACTION_EVENT, type ArtifactActionDetail } from "@/lib/artifactBridge";
import { parseRosterEntry, type RosterEntry } from "@/lib/participantTurn";
import { cn } from "@/lib/utils";
import { fileContentText, workspaceSidebarSource } from "@/lib/workspaceSidebarSource";
import {
  type Author,
  MAIN_AGENT_ID,
  type ReviewFile,
  type ReviewThread,
  USER_ID,
  addReply,
  addThread,
  authorOf,
  authorsFrom,
  deleteThread,
  parseReview,
  resolveMentions,
  routingMessage,
  serializeReview,
  setResolved,
  sidecarPath,
  waitingOn,
} from "./reviewModel";
import { setReviewPanelOpen } from "./reviewRailState";
import {
  type ThreadHighlightState,
  clearFreshEdits,
  findQuote,
  freshEditCount,
  redrawThreads,
} from "./TipTapReviewDecorations";
import {
  type SuggestionRange,
  decideSuggestions,
  findSuggestions,
  isSuggesting,
  setSuggesting,
} from "./TipTapSuggestions";

const PARTICIPANTS_FOLDER = "participants";

/** Colours for authors' suggestions, by kind; participants get one each, in roster order.
 * omnigent-slim: design tokens from design/tokens.json, so they follow the design language. */
const AGENT_HUES = [1, 2, 3, 4, 5].map((n) => `var(--pa-author-${n})`);
const PERSON_HUES = [6, 7, 8].map((n) => `var(--pa-author-${n})`);

function authorColor(author: Author, index: number): string {
  if (author.kind === "you") return "var(--pa-you)";
  if (author.kind === "main") return "var(--pa-agent)";
  const hues = author.kind === "person" ? PERSON_HUES : AGENT_HUES;
  return hues[index % hues.length];
}

/** The participant roster, read from `participants/` like the Session panel does. */
function useRoster(sessionId: string): RosterEntry[] {
  const { data } = useQuery({
    queryKey: ["slim-review-roster", sessionId],
    queryFn: async ({ signal }) => {
      const source = workspaceSidebarSource();
      let listing;
      try {
        listing = await source.listDirectory(sessionId, PARTICIPANTS_FOLDER, 200, signal);
      } catch {
        return [];
      }
      const files = listing.data.filter(
        (f) => f.type === "file" && f.name.endsWith(".md") && !/^(_|README|\.)/.test(f.name),
      );
      const entries = await Promise.all(
        files.map(async (file) => {
          try {
            const text = fileContentText(await source.readFile(sessionId, file.path, signal));
            return text === null ? null : parseRosterEntry(file.name.replace(/\.md$/, ""), text);
          } catch {
            return null;
          }
        }),
      );
      return entries
        .filter((e): e is RosterEntry => e !== null)
        .sort((a, b) => a.name.localeCompare(b.name));
    },
    staleTime: 30_000,
    retry: false,
  });
  return data ?? [];
}

/** Re-render on every editor transaction, at most once a frame. */
function useEditorTick(editor: Editor | null): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!editor) return;
    let frame = 0;
    const bump = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        setTick((t) => t + 1);
      });
    };
    editor.on("transaction", bump);
    return () => {
      editor.off("transaction", bump);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [editor]);
  return tick;
}

function AuthorMark({ author, color }: { author: Author; color: string }) {
  if (author.kind === "agent" || author.kind === "person") {
    return (
      <ParticipantMark
        name={author.name}
        kind={author.kind}
        standIn={author.standIn}
        className="size-5 text-[9px]"
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="inline-grid size-5 shrink-0 place-items-center rounded-full text-[9px] font-bold text-white"
      style={{ background: color }}
    >
      {author.kind === "main" ? "C" : author.name.charAt(0).toUpperCase()}
    </span>
  );
}

function authorTag(author: Author): string {
  if (author.kind === "you") return "You";
  if (author.kind === "main") return "Agent";
  if (author.standIn) return "Stand-in";
  return author.kind === "person" ? "Person" : "Agent";
}

/** Highlight @mentions in a message. */
function MessageText({ text, authors }: { text: string; authors: Map<string, Author> }) {
  const names = [...authors.values()]
    .filter((a) => a.kind !== "you")
    .flatMap((a) => [a.name, a.id, a.name.split(" ")[0]]);
  names.push("Claude");
  const pattern = new RegExp(
    `(@(?:${names
      .map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .sort((a, b) => b.length - a.length)
      .join("|")}))`,
    "gi",
  );
  return (
    <>
      {text.split(pattern).map((part, i) =>
        i % 2 === 1 ? (
          // oxlint-disable-next-line react/no-array-index-key -- split parts have no identity of their own
          <span key={`m${i}`} className="font-semibold text-sky-700 dark:text-sky-300">
            {part}
          </span>
        ) : (
          // oxlint-disable-next-line react/no-array-index-key -- split parts have no identity of their own
          <span key={`t${i}`}>{part}</span>
        ),
      )}
    </>
  );
}

/** A text box that offers participants after "@". Enter sends; Shift+Enter is a new line. */
function MentionBox({
  authors,
  placeholder,
  onSubmit,
  submitLabel,
  autoFocus,
  onCancel,
}: {
  authors: Map<string, Author>;
  placeholder: string;
  onSubmit: (text: string) => void;
  submitLabel: string;
  autoFocus?: boolean;
  onCancel?: () => void;
}) {
  const [value, setValue] = useState("");
  const [query, setQuery] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const ref = useRef<HTMLTextAreaElement>(null);
  const options = useMemo(() => {
    if (query === null) return [];
    const q = query.toLowerCase();
    return [...authors.values()].filter(
      (a) =>
        a.kind !== "you" &&
        (a.name.toLowerCase().startsWith(q) ||
          a.id.startsWith(q) ||
          a.role.toLowerCase().includes(q)),
    );
  }, [authors, query]);

  const onChange = (next: string) => {
    setValue(next);
    const caret = ref.current?.selectionStart ?? next.length;
    const match = /@([\w-]{0,20})$/.exec(next.slice(0, caret));
    setQuery(match ? match[1] : null);
    setIndex(0);
  };
  const pick = (author: Author) => {
    const el = ref.current;
    const caret = el?.selectionStart ?? value.length;
    const before = value.slice(0, caret).replace(/@[\w-]{0,20}$/, `@${author.name} `);
    const next = before + value.slice(caret);
    setValue(next);
    setQuery(null);
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(before.length, before.length);
    });
  };
  const submit = () => {
    const text = value.trim();
    if (!text) return;
    onSubmit(text);
    setValue("");
    setQuery(null);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (options.length) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        setIndex(
          (i) => (i + (event.key === "ArrowDown" ? 1 : -1) + options.length) % options.length,
        );
        return;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        pick(options[index]);
        return;
      }
    }
    if (event.key === "Escape") {
      if (query !== null) setQuery(null);
      else onCancel?.();
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="relative mt-2">
      <textarea
        ref={ref}
        value={value}
        autoFocus={autoFocus}
        rows={2}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => setTimeout(() => setQuery(null), 150)}
        className="w-full resize-y rounded-md border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-ring"
      />
      {options.length > 0 && (
        <div
          className="absolute left-0 right-0 top-full z-30 mt-1 rounded-md border border-border bg-popover p-1 shadow-lg"
          role="listbox"
        >
          {options.map((a, i) => (
            <button
              key={a.id}
              type="button"
              role="option"
              aria-selected={i === index}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(a);
              }}
              className={cn(
                "flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm",
                i === index && "bg-muted",
              )}
            >
              <AuthorMark author={a} color={authorColor(a, 0)} />
              <span className="min-w-0 flex-1">
                <span className="font-medium">{a.name}</span>{" "}
                <span className="text-xs text-muted-foreground">{authorTag(a)}</span>
                {a.role && (
                  <span className="block truncate text-xs text-muted-foreground">{a.role}</span>
                )}
              </span>
            </button>
          ))}
        </div>
      )}
      <div className="mt-1.5 flex gap-1.5">
        <button
          type="button"
          onClick={submit}
          disabled={!value.trim()}
          className="rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground disabled:opacity-50"
        >
          {submitLabel}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md px-2.5 py-1 text-xs hover:bg-muted"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

/** A small "Comment" button beside the selected text. */
function FloatingCommentButton({ editor, onClick }: { editor: Editor; onClick: () => void }) {
  const { from, to, empty } = editor.state.selection;
  if (empty || (!editor.isFocused && !editor.view.hasFocus())) return null;
  let coords;
  try {
    coords = editor.view.coordsAtPos(to);
    const start = editor.view.coordsAtPos(from);
    coords = { left: Math.max(coords.left, start.left), top: Math.min(coords.top, start.top) };
  } catch {
    return null;
  }
  return createPortal(
    <button
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      style={{ position: "fixed", left: coords.left + 8, top: coords.top - 34, zIndex: 50 }}
      className="flex items-center gap-1 rounded-md border border-border bg-popover px-2 py-1 text-xs font-medium shadow-md hover:bg-muted"
    >
      <MessageSquarePlus className="size-3.5 text-amber-600" /> Comment
    </button>,
    document.body,
  );
}

interface ReviewPanelProps {
  editor: Editor | null;
  conversationId: string;
  path: string;
  canEdit: boolean;
  highlightRef: RefObject<ThreadHighlightState | null>;
}

export function ReviewPanel({
  editor,
  conversationId,
  path,
  canEdit,
  highlightRef,
}: ReviewPanelProps) {
  useEditorTick(editor);
  const roster = useRoster(conversationId);
  const authors = useMemo(() => authorsFrom(roster), [roster]);
  const colors = useMemo(() => {
    const map = new Map<string, string>();
    let agents = 0;
    let people = 0;
    for (const a of authors.values()) {
      map.set(
        a.id,
        authorColor(a, a.kind === "person" ? people++ : a.kind === "agent" ? agents++ : 0),
      );
    }
    return map;
  }, [authors]);
  const colorOf = (id: string | null) => colors.get(id ?? "") ?? "var(--pa-author-1)";

  // The sidecar file. A missing file is an empty review.
  const reviewPath = sidecarPath(path);
  const sidecar = useFileContent(conversationId, reviewPath, { visible: true, retry: false });
  const [optimistic, setOptimistic] = useState<ReviewFile | null>(null);
  const review = optimistic ?? parseReview(sidecar.data ? fileContentText(sidecar.data) : null);
  useEffect(() => setOptimistic(null), [sidecar.data]);
  const write = useWriteFileContent(conversationId);

  /** Read the latest sidecar, apply `change`, write it back. */
  const update = useCallback(
    async (change: (data: ReviewFile) => ReviewFile) => {
      let latest: ReviewFile;
      try {
        latest = parseReview(fileContentText(await fetchFileContent(conversationId, reviewPath)));
      } catch {
        latest = parseReview(null);
      }
      const next = change(latest);
      setOptimistic(next);
      await write.mutateAsync({ path: reviewPath, content: serializeReview(next) });
      return next;
    },
    [conversationId, reviewPath, write],
  );

  const [tab, setTab] = useState<"comments" | "changes">("comments");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draftQuote, setDraftQuote] = useState<string | null>(null);
  const [open, setOpen] = useState<boolean | null>(null);
  const threadRefs = useRef(new Map<string, HTMLDivElement>());

  // Keep the editor's thread highlights in step with the file.
  useEffect(() => {
    highlightRef.current = {
      threads: review.threads,
      activeId,
      onClick: (id) => {
        setActiveId(id);
        setTab("comments");
        setOpen(true);
        threadRefs.current.get(id)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      },
    };
    if (editor && !editor.isDestroyed) redrawThreads(editor.view as never);
  }, [editor, review, activeId, highlightRef]);

  const suggestions: SuggestionRange[] =
    editor && !editor.isDestroyed ? findSuggestions(editor.state.doc) : [];
  // A removal straight followed by an addition from the same author is one replacement.
  const changes: SuggestionRange[][] = [];
  for (const s of suggestions) {
    const last = changes[changes.length - 1];
    const prev = last?.[last.length - 1];
    if (
      last &&
      last.length === 1 &&
      prev.kind === "delete" &&
      s.kind === "insert" &&
      prev.to === s.from &&
      prev.by === s.by
    )
      last.push(s);
    else changes.push([s]);
  }
  const fresh = editor && !editor.isDestroyed ? freshEditCount(editor.state) : 0;
  const openThreads = review.threads.filter((t) => !t.resolved);
  const suggesting = isSuggesting(editor);
  const selection =
    editor && !editor.isDestroyed && !editor.state.selection.empty
      ? editor.state.doc
          .textBetween(editor.state.selection.from, editor.state.selection.to, " ")
          .trim()
      : "";

  // Opens by itself when there is something to review; the user's choice wins after that.
  const hasContent = openThreads.length > 0 || suggestions.length > 0 || fresh > 0;
  const isOpen = open ?? hasContent;

  const send = (text: string) => {
    window.dispatchEvent(
      new CustomEvent<ArtifactActionDetail>(ARTIFACT_ACTION_EVENT, { detail: { text } }),
    );
  };

  const postComment = async (text: string) => {
    if (!draftQuote) return;
    const mentions = resolveMentions(text, authors);
    const quote = draftQuote;
    setDraftQuote(null);
    const next = await update((data) => addThread(data, quote, text, mentions));
    const thread = next.threads[next.threads.length - 1];
    setActiveId(thread.id);
    if (mentions.length) send(routingMessage(path, thread.id, mentions, authors));
  };
  const postReply = async (thread: ReviewThread, text: string) => {
    const mentions = resolveMentions(text, authors);
    await update((data) => addReply(data, thread.id, text, mentions));
    if (mentions.length) send(routingMessage(path, thread.id, mentions, authors));
  };

  const startComment = () => {
    if (!selection) return;
    setDraftQuote(selection.length > 300 ? selection.slice(0, 300) : selection);
    setTab("comments");
    setOpen(true);
  };

  const focusThread = (thread: ReviewThread) => {
    setActiveId(thread.id);
    if (!editor) return;
    const range = findQuote(editor.state.doc, thread.anchor.quote, thread.anchor.occurrence ?? 1);
    if (range) {
      const dom = editor.view.domAtPos(range.from).node as HTMLElement;
      (dom.nodeType === 1 ? dom : dom.parentElement)?.scrollIntoView({
        block: "center",
        behavior: "smooth",
      });
    }
  };

  // Clicking suggested text in the document shows it in the Changes tab.
  useEffect(() => {
    if (!editor) return;
    const dom = editor.view.dom;
    const onClick = (event: MouseEvent) => {
      if ((event.target as HTMLElement).closest?.(".md-suggestion")) {
        setTab("changes");
        setOpen(true);
      }
    };
    dom.addEventListener("click", onClick);
    return () => dom.removeEventListener("click", onClick);
  }, [editor]);

  // Per-author colours for the suggestion marks in the editor.
  const markStyles = [...colors.entries()]
    .map(
      ([id, color]) =>
        `.tiptap-md-content .md-suggestion[data-by="${CSS.escape(id)}"]{--md-suggestion-color:${color}}`,
    )
    .join("\n");

  // Tell the app shell, so the rail widens while the panel is open.
  const railId = useRef(Symbol("review-panel")).current;
  useEffect(() => {
    setReviewPanelOpen(railId, isOpen);
  }, [railId, isOpen]);
  useEffect(() => () => setReviewPanelOpen(railId, false), [railId]);

  const floating =
    canEdit && editor && !editor.isDestroyed && selection && !draftQuote ? (
      <FloatingCommentButton editor={editor} onClick={startComment} />
    ) : null;

  if (!isOpen) {
    return (
      <div className="flex w-9 shrink-0 flex-col items-center gap-2 border-l border-border py-3">
        <style>{markStyles}</style>
        {floating}
        <button
          type="button"
          title="Review: comments and suggested changes"
          onClick={() => setOpen(true)}
          className="flex flex-col items-center gap-1 rounded px-1 py-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <MessageSquarePlus className="size-4" />
          {hasContent && (
            <span className="rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
              {openThreads.length + changes.length}
            </span>
          )}
        </button>
        {selection && canEdit && (
          <button
            type="button"
            title="Comment on the selection"
            onMouseDown={(e) => e.preventDefault()}
            onClick={startComment}
            className="rounded p-1 text-muted-foreground hover:bg-muted"
          >
            <MessageSquarePlus className="size-4 text-amber-600" />
          </button>
        )}
      </div>
    );
  }

  return (
    <aside
      className="flex w-80 shrink-0 flex-col border-l border-border bg-muted/30"
      aria-label="Review"
    >
      <style>{markStyles}</style>
      {floating}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <span className="text-sm font-semibold">Review</span>
        {canEdit && editor && (
          <div
            className="ml-auto inline-flex overflow-hidden rounded-md border border-border text-xs"
            role="group"
            aria-label="Editing mode"
          >
            {(
              [
                ["Editing", false],
                ["Suggesting", true],
              ] as const
            ).map(([label, on]) => (
              <button
                key={label}
                type="button"
                aria-pressed={suggesting === on}
                title={
                  on
                    ? "Your edits are shown as suggestions for others to accept"
                    : "Your edits change the document directly"
                }
                onClick={() => setSuggesting(editor, on)}
                className={cn(
                  "px-2 py-1",
                  suggesting === on ? "bg-foreground text-background" : "hover:bg-muted",
                )}
              >
                {label}
              </button>
            ))}
          </div>
        )}
        <button
          type="button"
          title="Hide"
          onClick={() => setOpen(false)}
          className={cn("rounded p-1 hover:bg-muted", !(canEdit && editor) && "ml-auto")}
        >
          <ChevronRight className="size-4" />
        </button>
      </div>

      {fresh > 0 && editor && (
        <div className="mx-3 mt-3 rounded-md border border-violet-400/60 bg-violet-500/10 px-3 py-2 text-sm">
          <span className="font-medium">Claude</span> changed {fresh} passage{fresh > 1 ? "s" : ""}{" "}
          while you had this open.
          <button
            type="button"
            onClick={() => clearFreshEdits(editor.view as never)}
            className="ml-2 rounded border border-border bg-background px-2 py-0.5 text-xs hover:bg-muted"
          >
            Mark as seen
          </button>
        </div>
      )}

      <div className="flex border-b border-border px-1 pt-2 text-sm" role="tablist">
        {(
          [
            ["comments", `Comments${openThreads.length ? ` (${openThreads.length})` : ""}`],
            ["changes", `Changes${changes.length ? ` (${changes.length})` : ""}`],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={cn(
              "flex-1 border-b-2 px-2 pb-1.5",
              tab === key
                ? "border-foreground font-semibold"
                : "border-transparent text-muted-foreground",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-3">
        {tab === "comments" && (
          <>
            {canEdit && !draftQuote && (
              <button
                type="button"
                disabled={!selection}
                onMouseDown={(e) => e.preventDefault()}
                onClick={startComment}
                className="mb-3 flex w-full items-center gap-1.5 rounded-md border border-dashed border-border px-2 py-1.5 text-left text-sm text-muted-foreground enabled:hover:bg-muted disabled:opacity-60"
              >
                <MessageSquarePlus className="size-4 shrink-0" />
                <span className="truncate">
                  {selection
                    ? `Comment on “${selection.slice(0, 40)}${selection.length > 40 ? "…" : ""}”`
                    : "Select text to comment on it"}
                </span>
              </button>
            )}
            {draftQuote && (
              <div className="mb-3 rounded-lg border border-amber-400 bg-background p-2.5">
                <div className="border-l-2 border-amber-400 pl-2 text-xs text-muted-foreground">
                  {draftQuote}
                </div>
                <MentionBox
                  authors={authors}
                  autoFocus
                  placeholder="Comment, or @ someone to ask them"
                  submitLabel="Comment"
                  onSubmit={(t) => void postComment(t)}
                  onCancel={() => setDraftQuote(null)}
                />
              </div>
            )}
            {review.threads.length === 0 && !draftQuote && (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">
                No comments yet. Select text and comment; type @ to ask a participant.
              </p>
            )}
            {[...openThreads, ...review.threads.filter((t) => t.resolved)].map((thread) => {
              const waiting = waitingOn(thread);
              const own = thread.messages.every((m) => m.by === USER_ID);
              return (
                <div
                  key={thread.id}
                  ref={(el) => {
                    if (el) threadRefs.current.set(thread.id, el);
                    else threadRefs.current.delete(thread.id);
                  }}
                  onClick={(e) => {
                    if (!(e.target as HTMLElement).closest("button,textarea")) focusThread(thread);
                  }}
                  className={cn(
                    "mb-2.5 rounded-lg border bg-background p-2.5",
                    thread.id === activeId
                      ? "border-amber-400 ring-2 ring-amber-200 dark:ring-amber-900"
                      : "border-border",
                    thread.resolved && "opacity-60",
                  )}
                >
                  <div className="flex items-start gap-1">
                    <div className="flex-1 border-l-2 border-amber-400 pl-2 text-xs text-muted-foreground">
                      {thread.anchor.quote}
                    </div>
                    {canEdit && (
                      <button
                        type="button"
                        title={thread.resolved ? "Reopen" : "Resolve"}
                        onClick={() =>
                          void update((d) => setResolved(d, thread.id, !thread.resolved))
                        }
                        className="rounded p-1 text-muted-foreground hover:bg-muted"
                      >
                        {thread.resolved ? (
                          <RotateCcw className="size-3.5" />
                        ) : (
                          <Check className="size-3.5" />
                        )}
                      </button>
                    )}
                    {canEdit && own && (
                      <button
                        type="button"
                        title="Delete"
                        onClick={() => void update((d) => deleteThread(d, thread.id))}
                        className="rounded p-1 text-muted-foreground hover:bg-muted"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    )}
                  </div>
                  {thread.messages.map((msg) => {
                    const author = authorOf(authors, msg.by);
                    return (
                      <div key={msg.id} className="mt-2 flex gap-2">
                        <AuthorMark author={author} color={colorOf(msg.by)} />
                        <div className="min-w-0 flex-1">
                          <div className="text-xs">
                            <span className="font-semibold">{author.name}</span>{" "}
                            <span className="rounded border border-border px-1 text-[10px] text-muted-foreground">
                              {authorTag(author)}
                            </span>
                          </div>
                          <div className="whitespace-pre-wrap text-sm">
                            <MessageText text={msg.text} authors={authors} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {waiting.map((id) => (
                    <div key={id} className="mt-2 text-xs italic text-muted-foreground">
                      Waiting for {authorOf(authors, id).name}…
                    </div>
                  ))}
                  {canEdit && !thread.resolved && (
                    <MentionBox
                      authors={authors}
                      placeholder="Reply, or @ someone"
                      submitLabel="Reply"
                      onSubmit={(t) => void postReply(thread, t)}
                    />
                  )}
                </div>
              );
            })}
          </>
        )}

        {tab === "changes" && editor && (
          <>
            {suggestions.length === 0 && (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">
                No suggested changes. Switch to Suggesting to propose edits; participants always
                suggest.
              </p>
            )}
            {changes.map((group) => {
              const s = group[0];
              const author = authorOf(authors, s.by);
              const replaced = group.length === 2;
              const note = group.map((g) => g.note).find(Boolean);
              return (
                <div
                  key={s.key}
                  className="mb-2 rounded-lg border border-border bg-background p-2.5 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <AuthorMark author={author} color={colorOf(s.by)} />
                    <span className="font-semibold">{author.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {replaced ? "replaced" : s.kind === "insert" ? "added" : "removed"}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      editor.commands.setTextSelection({
                        from: s.from,
                        to: group[group.length - 1].to,
                      });
                      editor.commands.scrollIntoView();
                    }}
                    className="mt-1 block w-full text-left"
                    style={{ color: colorOf(s.by) }}
                  >
                    {group.map((g, i) => (
                      <span
                        key={g.key}
                        className={cn(
                          "line-clamp-2",
                          g.kind === "delete" && "line-through opacity-80",
                        )}
                      >
                        {i === 1 && <span className="text-muted-foreground no-underline">→ </span>}“
                        {g.text}”
                      </span>
                    ))}
                  </button>
                  {note && <div className="mt-1 text-xs text-muted-foreground">{note}</div>}
                  {canEdit && (
                    <div className="mt-2 flex gap-1.5">
                      <button
                        type="button"
                        onClick={() => decideSuggestions(editor, group, true)}
                        className="flex items-center gap-1 rounded-md bg-primary px-2 py-0.5 text-xs text-primary-foreground"
                      >
                        <Check className="size-3" /> Accept
                      </button>
                      <button
                        type="button"
                        onClick={() => decideSuggestions(editor, group, false)}
                        className="flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-xs hover:bg-muted"
                      >
                        <X className="size-3" /> Reject
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
            {canEdit && changes.length > 1 && (
              <div className="flex gap-1.5">
                <button
                  type="button"
                  onClick={() => decideSuggestions(editor, suggestions, true)}
                  className="rounded-md border border-border px-2 py-1 text-xs hover:bg-muted"
                >
                  Accept all
                </button>
                <button
                  type="button"
                  onClick={() => decideSuggestions(editor, suggestions, false)}
                  className="rounded-md border border-border px-2 py-1 text-xs hover:bg-muted"
                >
                  Reject all
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}

export { MAIN_AGENT_ID };
