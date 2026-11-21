// omnigent-slim: the two file lists of the session panel.
//
// - Outputs: what the session has made, i.e. the files in the workspace's
//   `artifacts/` folder, newest first. Click one to open it in the viewer.
// - Context: the documents the user offers the agent, i.e. the files in the
//   workspace's `context/` folder. Tick some and "Add to message" writes file
//   mentions into the composer; nothing is sent until the user presses Send.
//
// - Workflow: where a structured workflow is, i.e. one card per small JSON
//   file in the workspace's `progress/` folder (written by `pa flow`): its
//   steps, the current one, and how many items are done.
// - People and agents: who the agent can call into the conversation, i.e. the
//   files in the workspace's `participants/` folder. Click one and a request
//   to check in with them lands in the composer.
//
// All read the workspace through the same listing the Files tab uses and poll
// while shown, so a file the agent writes appears without a reload.

import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { ARTIFACT_PROMPT_EVENT, type ArtifactPromptDetail } from "@/lib/artifactBridge";
import { ParticipantMark } from "@/components/chat/ParticipantTurn";
import { parseRosterEntry, type RosterEntry } from "@/lib/participantTurn";
import type { ListedEntry } from "@/lib/workspaceApi";
import { fileContentText, workspaceSidebarSource } from "@/lib/workspaceSidebarSource";
import { useSession } from "@/hooks/useSession";
import { useFileViewer } from "./FileViewerContext";

/** Workspace folders the panel reads. */
export const OUTPUTS_FOLDER = "artifacts";
export const CONTEXT_FOLDER = "context";
export const PARTICIPANTS_FOLDER = "participants";
export const PROGRESS_FOLDER = "progress";

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

/** What a `progress/*.json` file says about one workflow. */
export interface WorkflowProgress {
  path: string;
  workflow: string;
  subject: string;
  steps: string[];
  /** 1-based; past the last step means the workflow is finished. */
  current: number;
  note: string;
  counts: { done: number; total: number; noun: string; label: string; waiting: number } | null;
  /** Ids of the participants this workflow may call; ``null`` when it does not say. */
  participants: string[] | null;
}

/**
 * Read a progress file's text.
 *
 * :param path: Workspace path of the file, e.g. ``"progress/allowances--document-review.json"``.
 * :param text: Its JSON text.
 * :returns: The progress, or ``null`` when the text is not a workflow with steps.
 */
export function parseWorkflowProgress(path: string, text: string): WorkflowProgress | null {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof raw !== "object" || raw === null) return null;
  const data = raw as Record<string, unknown>;
  const steps = Array.isArray(data.steps)
    ? data.steps.filter((step): step is string => typeof step === "string").slice(0, 12)
    : [];
  if (steps.length === 0) return null;
  const label = (value: unknown) => (typeof value === "string" ? value.slice(0, 120) : "");
  const count = (value: unknown) =>
    typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0;
  const rawCounts =
    typeof data.counts === "object" && data.counts !== null
      ? (data.counts as Record<string, unknown>)
      : null;
  return {
    path,
    workflow: label(data.workflow) || "Workflow",
    subject: label(data.subject),
    steps,
    current: Math.min(steps.length + 1, Math.max(1, count(data.current) || 1)),
    note: label(data.note),
    participants: Array.isArray(data.participants)
      ? data.participants.filter((id): id is string => typeof id === "string")
      : null,
    counts:
      rawCounts && count(rawCounts.total) > 0
        ? {
            done: Math.min(count(rawCounts.done), count(rawCounts.total)),
            total: count(rawCounts.total),
            noun: label(rawCounts.noun) || "items",
            label: label(rawCounts.label) || "done",
            waiting: count(rawCounts.waiting),
          }
        : null,
  };
}

/** Workflows this session has moved, most recently moved first. */
function useWorkflows(sessionId: string): WorkflowProgress[] {
  const { session } = useSession(sessionId);
  const since = session?.createdAt ?? 0;
  const files = useFolderFiles(sessionId, PROGRESS_FOLDER).filter(
    (file) => file.name.endsWith(".json") && (file.modified_at ?? 0) >= since,
  );
  const key = files.map((file) => `${file.path}:${file.modified_at ?? 0}`).join("|");
  const { data } = useQuery({
    queryKey: ["slim-session-workflows", sessionId, key],
    queryFn: async ({ signal }) => {
      const entries = await Promise.all(
        files.map(async (file) => {
          try {
            const content = await workspaceSidebarSource().readFile(sessionId, file.path, signal);
            const text = fileContentText(content);
            return text === null ? null : parseWorkflowProgress(file.path, text);
          } catch {
            return null;
          }
        }),
      );
      return entries.filter((entry): entry is WorkflowProgress => entry !== null);
    },
    enabled: files.length > 0,
    // The folder listing only changes when a file's time does; keep the last cards meanwhile.
    placeholderData: (previous) => previous,
    retry: false,
  });
  return files.length > 0 ? (data ?? []) : [];
}

function WorkflowCard({ flow }: { flow: WorkflowProgress }) {
  const finished = flow.current > flow.steps.length;
  const counts = flow.counts;
  return (
    <div className="flex flex-col gap-1.5" data-testid="session-workflow">
      <p className="leading-tight">
        <span className="font-medium">{flow.workflow}</span>
        {flow.subject && <span className="text-muted-foreground"> · {flow.subject}</span>}
      </p>
      <ol className="flex flex-col gap-0.5">
        {flow.steps.map((step, index) => {
          const number = index + 1;
          const state = number < flow.current ? "done" : number === flow.current ? "current" : "todo";
          return (
            <li
              key={step}
              data-state={state}
              aria-current={state === "current" ? "step" : undefined}
              className="flex items-baseline gap-2"
            >
              <span
                aria-hidden="true"
                className={
                  state === "done"
                    ? "w-4 shrink-0 text-center text-emerald-600"
                    : state === "current"
                      ? "w-4 shrink-0 text-center font-mono text-xs font-bold"
                      : "w-4 shrink-0 text-center font-mono text-xs text-muted-foreground"
                }
              >
                {state === "done" ? "✓" : number}
              </span>
              <span className="min-w-0 flex-1">
                <span
                  className={
                    state === "current"
                      ? "font-medium"
                      : state === "done"
                        ? "text-muted-foreground"
                        : "text-muted-foreground/80"
                  }
                >
                  {step}
                </span>
                {state === "current" && flow.note && (
                  <span className="block text-xs text-muted-foreground">{flow.note}</span>
                )}
              </span>
            </li>
          );
        })}
      </ol>
      {counts && (
        <div className="flex flex-col gap-1">
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={counts.total}
            aria-valuenow={counts.done}
            aria-label={`${counts.done} of ${counts.total} ${counts.noun} ${counts.label}`}
            className="h-1.5 overflow-hidden rounded-full bg-muted"
          >
            <div
              className="h-full rounded-full bg-emerald-600"
              style={{ width: `${(counts.done / counts.total) * 100}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            {counts.done} of {counts.total} {counts.noun} {counts.label}
            {counts.waiting > 0 && ` · ${counts.waiting} waiting on you`}
            {finished && " · finished"}
          </p>
        </div>
      )}
      {!counts && finished && <p className="text-xs text-muted-foreground">Finished</p>}
    </div>
  );
}

/** Where each structured workflow of this session is. Hidden when there is none. */
function Workflows({ sessionId }: { sessionId: string }) {
  const flows = useWorkflows(sessionId);
  if (flows.length === 0) return null;
  return (
    <Section title="Workflow">
      <div className="flex flex-col gap-3">
        {flows.map((flow) => (
          <WorkflowCard key={flow.path} flow={flow} />
        ))}
      </div>
    </Section>
  );
}

/** The roster: one entry per readable file in `participants/`, by name. */
function useRoster(sessionId: string): RosterEntry[] {
  const files = useFolderFiles(sessionId, PARTICIPANTS_FOLDER).filter(
    (file) => file.name.endsWith(".md") && !/^(_|README)/.test(file.name),
  );
  const key = files.map((file) => `${file.path}:${file.modified_at ?? 0}`).join("|");
  const { data } = useQuery({
    queryKey: ["slim-session-roster", sessionId, key],
    queryFn: async ({ signal }) => {
      const entries = await Promise.all(
        files.map(async (file) => {
          try {
            const content = await workspaceSidebarSource().readFile(sessionId, file.path, signal);
            const text = fileContentText(content);
            return text === null ? null : parseRosterEntry(file.name.replace(/\.md$/, ""), text);
          } catch {
            return null;
          }
        }),
      );
      return entries.filter((entry): entry is RosterEntry => entry !== null);
    },
    enabled: files.length > 0,
    retry: false,
  });
  return [...(data ?? [])].sort((a, b) => a.name.localeCompare(b.name));
}

/** The composer text that asks the agent to bring a participant in. */
export function callMessage(entry: RosterEntry): string {
  // "@id" addresses the participant directly: they answer, not the session's agent.
  return `@${entry.id} `;
}

/** Other agents and people the agent can call into this conversation. */
function Roster({ sessionId }: { sessionId: string }) {
  const everyone = useRoster(sessionId);
  // A workflow can name who may take part in it. While one that does is under way,
  // the list shows those people; the rest of the roster is one click away.
  const limits = useWorkflows(sessionId)
    .map((flow) => flow.participants)
    .filter((ids): ids is string[] => ids !== null);
  const eligible = limits.length > 0 ? new Set(limits.flat()) : null;
  const [showAll, setShowAll] = useState(false);
  if (everyone.length === 0) return null;
  const roster = eligible && !showAll ? everyone.filter((entry) => eligible.has(entry.id)) : everyone;
  const others = everyone.length - roster.length;
  const call = (entry: RosterEntry) => {
    const detail: ArtifactPromptDetail = { text: callMessage(entry) };
    window.dispatchEvent(new CustomEvent(ARTIFACT_PROMPT_EVENT, { detail }));
  };
  return (
    <Section title="People and agents" count={roster.length}>
      <ul className="flex flex-col gap-0.5" data-testid="session-roster">
        {roster.map((entry) => (
          <li key={entry.id}>
            <button
              type="button"
              className="flex w-full min-w-0 cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-left hover:bg-muted focus-visible:outline-2"
              title={entry.callFor ? `Call for: ${entry.callFor}` : `Ask the agent to call ${entry.name}`}
              onClick={() => call(entry)}
            >
              <ParticipantMark
                name={entry.name}
                kind={entry.kind}
                standIn={entry.standIn}
                className="size-5 text-[9px]"
              />
              <span className="min-w-0 flex-1 truncate">
                {entry.name}
                <span className="ml-1.5 text-xs text-muted-foreground">{entry.role}</span>
              </span>
              {entry.standIn && (
                <span className="shrink-0 text-xs text-muted-foreground">stand-in</span>
              )}
            </button>
          </li>
        ))}
      </ul>
      {eligible && (others > 0 || showAll) && (
        <button
          type="button"
          className="cursor-pointer self-start rounded px-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
          onClick={() => setShowAll((value) => !value)}
        >
          {showAll ? "Show this workflow's only" : `${others} more on the roster`}
        </button>
      )}
    </Section>
  );
}

/** The Outputs, Context and People sections of the session panel. */
export function SessionOverviewFiles({ sessionId }: { sessionId: string }) {
  return (
    <>
      <Workflows sessionId={sessionId} />
      <Outputs sessionId={sessionId} />
      <Context sessionId={sessionId} />
      <Roster sessionId={sessionId} />
    </>
  );
}
