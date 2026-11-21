// omnigent-slim: the director's notes on a project's page (D-134).
//
// A director runs for days, across compactions and new sessions, so what it
// must not lose lives in two files it writes at checkpoints: where the
// project stands (`director/state.md`) and lasting facts (`director/memory.md`).
// The person reads and edits both here; the director re-reads them with
// `pa recap`, so the person's edit wins.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/identity";

export type NoteKey = "state" | "memory";

export interface DirectorNote {
  file: string;
  text: string;
  /** Seconds since the epoch the file was last written; null when it does not exist. */
  updated: number | null;
}

export interface DirectorNotes {
  exists: boolean;
  state: DirectorNote;
  memory: DirectorNote;
}

export const NOTE_TITLES: Record<NoteKey, string> = {
  state: "Where the project stands",
  memory: "What to remember",
};

function parseNote(raw: unknown, file: string): DirectorNote {
  const data = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
  return {
    file: typeof data.file === "string" ? data.file : file,
    text: typeof data.text === "string" ? data.text : "",
    updated: typeof data.updated === "number" ? data.updated : null,
  };
}

/** Read the `GET /v1/slim/director/notes` answer (also the body of a 409). */
export function parseDirectorNotes(raw: unknown): DirectorNotes {
  const data = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
  const state = parseNote(data.state, "director/state.md");
  const memory = parseNote(data.memory, "director/memory.md");
  return { exists: Boolean(data.exists) || state.updated !== null || memory.updated !== null, state, memory };
}

export type NoteBlock =
  | { kind: "heading"; text: string }
  | { kind: "item"; text: string }
  | { kind: "para"; text: string };

/**
 * The few markdown shapes the notes use, as blocks: `##` headings, `-` items
 * and paragraphs. The `#` title is dropped (the card has its own) and an
 * empty section is dropped with its heading, so a fresh state file reads as
 * its guidance line, not four bare headings.
 */
export function noteBlocks(text: string): NoteBlock[] {
  const blocks: NoteBlock[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length) blocks.push({ kind: "para", text: para.join(" ") });
    para = [];
  };
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (/^#\s/.test(line)) {
      flush();
    } else if (/^#{2,}\s/.test(line)) {
      flush();
      blocks.push({ kind: "heading", text: line.replace(/^#+\s+/, "") });
    } else if (/^[-*]\s/.test(line)) {
      flush();
      blocks.push({ kind: "item", text: line.slice(2).trim() });
    } else if (line === "") {
      flush();
    } else {
      para.push(line);
    }
  }
  flush();
  return blocks.filter(
    (block, i) => block.kind !== "heading" || (i + 1 < blocks.length && blocks[i + 1].kind !== "heading"),
  );
}

const key = (projectName: string) => ["slim-director-notes", projectName];

export function useDirectorNotes(projectName: string) {
  return useQuery<DirectorNotes>({
    queryKey: key(projectName),
    queryFn: async ({ signal }) => {
      const res = await authenticatedFetch(
        `/v1/slim/director/notes?project=${encodeURIComponent(projectName)}`,
        { signal },
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return parseDirectorNotes(await res.json());
    },
    enabled: Boolean(projectName),
    refetchInterval: 15000,
    retry: false,
  });
}

export class NoteConflict extends Error {
  constructor(readonly latest: DirectorNotes) {
    super("The director changed this note while you were editing.");
  }
}

export function useSaveDirectorNote(projectName: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (save: { note: NoteKey; text: string; base: number | null }) => {
      const res = await authenticatedFetch("/v1/slim/director/notes", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project: projectName, ...save }),
      });
      if (res.status === 409) {
        const body = (await res.json()) as { detail?: unknown };
        throw new NoteConflict(parseDirectorNotes(body.detail));
      }
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return parseDirectorNotes(await res.json());
    },
    onSuccess: (notes) => client.setQueryData(key(projectName), notes),
    onError: (error) => {
      if (error instanceof NoteConflict) client.setQueryData(key(projectName), error.latest);
    },
  });
}
