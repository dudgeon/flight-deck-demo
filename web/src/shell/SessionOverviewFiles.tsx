// omnigent-slim: the two file lists of the session panel.
//
// - Outputs: what the session has made, i.e. the files in the workspace's
//   `artifacts/` folder, newest first. Click one to open it in the viewer.
// - Context: the documents the user offers the agent, i.e. the files in the
//   workspace's `context/` folder. Tick some and "Add to message" writes file
//   mentions into the composer; nothing is sent until the user presses Send.
//
// Both read the workspace through the same listing the Files tab uses and poll
// while shown, so a file the agent writes appears without a reload.

import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { ARTIFACT_PROMPT_EVENT, type ArtifactPromptDetail } from "@/lib/artifactBridge";
import type { ListedEntry } from "@/lib/workspaceApi";
import { workspaceSidebarSource } from "@/lib/workspaceSidebarSource";
import { useSession } from "@/hooks/useSession";
import { useFileViewer } from "./FileViewerContext";

/** Workspace folders the panel reads. */
export const OUTPUTS_FOLDER = "artifacts";
export const CONTEXT_FOLDER = "context";

const MAX_ENTRIES = 200;
const POLL_MS = 5_000;
const COLLAPSED_ROWS = 5;

/** Files of one workspace folder, newest first; empty while loading or when it doesn't exist. */
function useFolderFiles(sessionId: string, folder: string): ListedEntry[] {
  const { data } = useQuery({
    queryKey: ["slim-session-folder", sessionId, folder],
    queryFn: async ({ signal }) => {
      try {
        const listing = await workspaceSidebarSource().listDirectory(
          sessionId,
          folder,
          MAX_ENTRIES,
          signal,
        );
        return listing.data;
      } catch {
        // A workspace without the folder simply has nothing to list.
        return [];
      }
    },
    refetchInterval: POLL_MS,
    retry: false,
  });
  return sortNewestFirst((data ?? []).filter(isListedFile));
}

function isListedFile(entry: ListedEntry): boolean {
  return entry.type === "file" && !entry.name.startsWith(".");
}

/** Newest first; files without a time last, by name. */
export function sortNewestFirst(entries: ListedEntry[]): ListedEntry[] {
  return [...entries].sort(
    (a, b) => (b.modified_at ?? 0) - (a.modified_at ?? 0) || a.name.localeCompare(b.name),
  );
}

/** "a-file-name.html" as "A file name", for lists where the extension is noise. */
export function displayName(name: string): string {
  const stem = name
    .replace(/\.[^.]+$/, "")
    .replace(/[-_]+/g, " ")
    .trim();
  return stem ? stem.charAt(0).toUpperCase() + stem.slice(1) : name;
}

/** "3 min ago" style age for a unix time in seconds. */
export function formatAge(seconds: number | null, nowMs: number = Date.now()): string {
  if (seconds === null) return "";
  const minutes = Math.max(0, Math.round((nowMs / 1000 - seconds) / 60));
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}

/** The composer text that points the agent at the chosen context files. */
export function contextMessage(paths: string[]): string {
  if (paths.length === 0) return "";
  const mentions = paths.map((path) => `@${path}`).join(" ");
  return paths.length === 1
    ? `Use ${mentions} as context for this session. `
    : `Use these files as context for this session: ${mentions} `;
}

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count?: number;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-1 border-t border-border pt-2">
      <h3 className="flex items-baseline justify-between text-xs font-medium tracking-wide text-muted-foreground uppercase">
        <span>{title}</span>
        {count !== undefined && count > 0 && <span className="font-mono">{count}</span>}
      </h3>
      {children}
    </section>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="text-xs text-muted-foreground">{children}</p>;
}

const ROW_BUTTON =
  "min-w-0 flex-1 cursor-pointer truncate rounded px-1 py-0.5 text-left hover:bg-muted focus-visible:outline-2";

/** Files the session has produced, split into this session's and older ones. */
function Outputs({ sessionId }: { sessionId: string }) {
  const openFile = useFileViewer();
  const { session } = useSession(sessionId);
  const files = useFolderFiles(sessionId, OUTPUTS_FOLDER);
  const [showAll, setShowAll] = useState(false);
  // The folder is shared by every session in this workspace, so only files
  // touched since this session began count as its own.
  const since = session?.createdAt ?? 0;
  const mine = files.filter((file) => (file.modified_at ?? 0) >= since);
  const earlier = files.filter((file) => (file.modified_at ?? 0) < since);
  const rows = showAll ? [...mine, ...earlier] : mine.slice(0, COLLAPSED_ROWS);
  const hidden = files.length - rows.length;
  return (
    <Section title="Outputs" count={mine.length}>
      {files.length === 0 && <Empty>What the agent makes in this session appears here.</Empty>}
      {files.length > 0 && mine.length === 0 && !showAll && (
        <Empty>Nothing from this session yet.</Empty>
      )}
      <ul className="flex flex-col" data-testid="session-outputs">
        {rows.map((file) => (
          <li key={file.path} className="flex items-baseline gap-2">
            <button
              type="button"
              className={ROW_BUTTON}
              title={file.path}
              onClick={() => openFile?.(file.path)}
            >
              {displayName(file.name)}
            </button>
            <span className="shrink-0 font-mono text-xs text-muted-foreground tabular-nums">
              {formatAge(file.modified_at)}
            </span>
          </li>
        ))}
      </ul>
      {(hidden > 0 || showAll) && (
        <button
          type="button"
          className="cursor-pointer self-start rounded px-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
          onClick={() => setShowAll((value) => !value)}
        >
          {showAll ? "Show this session only" : `Show ${hidden} more from this folder`}
        </button>
      )}
    </Section>
  );
}

/** Documents the user can point the agent at. */
function Context({ sessionId }: { sessionId: string }) {
  const openFile = useFileViewer();
  const files = useFolderFiles(sessionId, CONTEXT_FOLDER);
  const [picked, setPicked] = useState<ReadonlySet<string>>(new Set());
  const [added, setAdded] = useState<ReadonlySet<string>>(new Set());
  const chosen = files.filter((file) => picked.has(file.path)).map((file) => file.path);
  const toggle = (path: string) =>
    setPicked((current) => {
      const next = new Set(current);
      if (!next.delete(path)) next.add(path);
      return next;
    });
  const addToMessage = () => {
    const detail: ArtifactPromptDetail = { text: contextMessage(chosen) };
    window.dispatchEvent(new CustomEvent(ARTIFACT_PROMPT_EVENT, { detail }));
    setAdded((current) => new Set([...current, ...chosen]));
    setPicked(new Set());
  };
  return (
    <Section title="Context" count={files.length}>
      {files.length === 0 && (
        <Empty>
          Put documents in the <code className="font-mono">{CONTEXT_FOLDER}/</code> folder to offer
          them to the agent here.
        </Empty>
      )}
      <ul className="flex flex-col" data-testid="session-context">
        {files.map((file) => (
          <li key={file.path} className="flex items-center gap-1.5">
            <input
              type="checkbox"
              className="size-3.5 shrink-0 accent-[var(--brand-navy,currentColor)]"
              checked={picked.has(file.path)}
              onChange={() => toggle(file.path)}
              aria-label={`Use ${file.name} as context`}
            />
            <button
              type="button"
              className={ROW_BUTTON}
              title={file.path}
              onClick={() => openFile?.(file.path)}
            >
              {file.name}
            </button>
            {added.has(file.path) && (
              <span className="shrink-0 text-xs text-muted-foreground">added</span>
            )}
          </li>
        ))}
      </ul>
      {files.length > 0 && (
        <button
          type="button"
          disabled={chosen.length === 0}
          className="cursor-pointer self-start rounded border border-border px-2 py-0.5 text-xs hover:bg-muted disabled:cursor-default disabled:opacity-50"
          onClick={addToMessage}
        >
          {chosen.length > 0 ? `Add ${chosen.length} to message` : "Add to message"}
        </button>
      )}
    </Section>
  );
}

/** The Outputs and Context sections of the session panel. */
export function SessionOverviewFiles({ sessionId }: { sessionId: string }) {
  return (
    <>
      <Outputs sessionId={sessionId} />
      <Context sessionId={sessionId} />
    </>
  );
}
