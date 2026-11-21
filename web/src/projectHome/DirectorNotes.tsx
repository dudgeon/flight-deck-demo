// omnigent-slim: "Director's notes" on a project's page (D-128).
//
// What the director keeps so it can pick up after a compaction or in a new
// session: where the project stands and what to remember. It is here so the
// person can see exactly what the director will act on, and correct it. It
// shows only once a director has written something, and starts folded, since
// it is for checking, not for every visit.

import { useState } from "react";
import { cn } from "@/lib/utils";
import { formatAge } from "@/shell/SessionOverviewFiles";
import {
  type DirectorNote,
  NOTE_TITLES,
  NoteConflict,
  type NoteKey,
  noteBlocks,
  useDirectorNotes,
  useSaveDirectorNote,
} from "./directorNotes";

const BUTTON =
  "rounded-[var(--pa-r)] px-2.5 py-1 text-[13px] font-medium outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--pa-navy)]";
const PRIMARY = "bg-[var(--pa-navy)] text-[var(--pa-on-navy)] hover:bg-[var(--pa-navy-hover)]";
const QUIET = "text-[var(--pa-ink)] hover:bg-[var(--pa-sunk)]";

function ago(seconds: number): string {
  const age = formatAge(seconds);
  return age === "now" ? "just now" : `${age} ago`;
}

function NoteBody({ text }: { text: string }) {
  // The same line can appear twice; number repeats so each key is its own.
  const seen = new Map<string, number>();
  const blocks = noteBlocks(text).map((block) => {
    const base = `${block.kind}:${block.text}`;
    const n = (seen.get(base) ?? 0) + 1;
    seen.set(base, n);
    return { ...block, key: `${base}:${n}` };
  });
  if (blocks.length === 0) return <p className="text-[var(--pa-ink-3)]">Nothing written yet.</p>;
  return (
    <div className="flex flex-col gap-1.5 text-[var(--pa-ink-2)]">
      {blocks.map((block) =>
        block.kind === "heading" ? (
          <h4 key={block.key} className="pt-1 text-[11px] font-semibold text-[var(--pa-ink-3)]">
            {block.text}
          </h4>
        ) : block.kind === "item" ? (
          <p key={block.key} className="flex gap-1.5 text-[var(--pa-ink)]">
            <span aria-hidden className="text-[var(--pa-ink-3)]">
              ·
            </span>
            <span>{block.text}</span>
          </p>
        ) : (
          <p key={block.key}>{block.text}</p>
        ),
      )}
    </div>
  );
}

function NoteCard({
  noteKey,
  note,
  projectName,
}: {
  noteKey: NoteKey;
  note: DirectorNote;
  projectName: string;
}) {
  const save = useSaveDirectorNote(projectName);
  const [draft, setDraft] = useState<{ text: string; base: number | null } | null>(null);
  const conflict = save.error instanceof NoteConflict;
  const title = NOTE_TITLES[noteKey];

  function startEditing() {
    save.reset();
    setDraft({ text: note.text, base: note.updated });
  }

  function submit() {
    if (!draft) return;
    save.mutate(
      { note: noteKey, text: draft.text, base: draft.base },
      { onSuccess: () => setDraft(null) },
    );
  }

  return (
    <article
      data-testid={`director-note-${noteKey}`}
      aria-label={title}
      className="flex min-w-[18rem] flex-1 flex-col gap-2 rounded-[var(--pa-r-panel)] border border-[var(--pa-line)] bg-[var(--pa-surface)] p-3"
    >
      <header className="flex items-center gap-2">
        <h3 className="min-w-0 flex-1 truncate font-semibold text-[var(--pa-ink)]">{title}</h3>
        {note.updated !== null && (
          <span className="shrink-0 text-[12px] text-[var(--pa-ink-3)]">{ago(note.updated)}</span>
        )}
        {draft === null && (
          <button type="button" className={cn(BUTTON, QUIET)} onClick={startEditing}>
            Edit
          </button>
        )}
      </header>
      {draft === null ? (
        <NoteBody text={note.text} />
      ) : (
        <div className="flex flex-col gap-2">
          <textarea
            aria-label={`Edit ${title.toLowerCase()}`}
            value={draft.text}
            onChange={(event) => setDraft({ ...draft, text: event.target.value })}
            rows={Math.min(18, Math.max(6, draft.text.split("\n").length + 1))}
            className="w-full resize-y rounded-[var(--pa-r)] border border-[var(--pa-line-strong)] bg-[var(--pa-bg)] p-2 font-[family-name:var(--pa-mono)] text-[12px] text-[var(--pa-ink)] outline-none focus-visible:border-[var(--pa-navy)]"
          />
          {conflict && (
            <p role="alert" className="rounded-[var(--pa-r)] bg-[var(--pa-attn-soft)] p-2 text-[var(--pa-ink)]">
              The director changed this note while you were editing. Your text is still here; copy
              what you need, then press Start again to edit the newest version.
            </p>
          )}
          {save.error && !conflict && (
            <p role="alert" className="text-[var(--pa-fail)]">
              Could not save: {save.error.message}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className={cn(BUTTON, QUIET)}
              onClick={() => {
                save.reset();
                setDraft(null);
              }}
            >
              Cancel
            </button>
            {conflict ? (
              <button type="button" className={cn(BUTTON, PRIMARY)} onClick={startEditing}>
                Start again
              </button>
            ) : (
              <button
                type="button"
                className={cn(BUTTON, PRIMARY)}
                disabled={save.isPending}
                onClick={submit}
              >
                {save.isPending ? "Saving" : "Save"}
              </button>
            )}
          </div>
        </div>
      )}
    </article>
  );
}

export function DirectorNotes({ projectName }: { projectName: string }) {
  const { data } = useDirectorNotes(projectName);
  const [open, setOpen] = useState(false);
  if (!data?.exists) return null;
  const latest = Math.max(data.state.updated ?? 0, data.memory.updated ?? 0);
  return (
    <section
      aria-label="Director's notes"
      data-testid="director-notes"
      className="flex shrink-0 flex-col gap-2 px-4 pb-3 font-[family-name:var(--pa-font)] text-[13px]"
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 self-start rounded-[var(--pa-r)] py-0.5 text-left outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--pa-navy)]"
      >
        <span aria-hidden className={cn("inline-block text-[var(--pa-ink-3)] transition-transform", open && "rotate-90")}>
          ›
        </span>
        <span className="font-semibold text-[var(--pa-ink)]">Director's notes</span>
        <span className="text-[var(--pa-ink-3)]">
          {latest > 0 ? `Updated ${ago(latest)} · ` : ""}what Aviator picks up from after a break
        </span>
      </button>
      {open && (
        <div className="flex flex-wrap gap-3">
          <NoteCard noteKey="state" note={data.state} projectName={projectName} />
          <NoteCard noteKey="memory" note={data.memory} projectName={projectName} />
        </div>
      )}
    </section>
  );
}
