// omnigent-slim: the direct line from a director's chat to a thread (D-116).
//
// Aviator directs a project and runs each workflow in a thread. While a thread
// has the floor, the person stays in the director's chat and still does the
// work: the thread's turns appear there inside a rail (D-91), and what the
// person types goes straight to the thread. Aviator is not in the path, so no
// turn waits on a second agent. `@aviator` at the start of a message, or the
// strip's switch, sends to Aviator instead; its answer shows outside the rail
// (D-92).
//
// The server names the thread with the floor at `GET /v1/slim/directors/<id>`.

import { useQuery } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import { authenticatedFetch } from "@/lib/identity";
import type { Bubble } from "@/lib/renderItems";
import { parseProjectRun, type ProjectRun } from "@/projectHome/projectRuns";

/** The run with the floor in `GET /v1/slim/directors/<id>`; null when no thread has it. */
export function parseDirectLine(raw: unknown): ProjectRun | null {
  if (typeof raw !== "object" || raw === null) return null;
  const run = parseProjectRun((raw as { line?: unknown }).line);
  return run !== null && run.session !== null ? run : null;
}

const REFRESH_MS = 5000;

/** The run that has the floor in this director's chat, re-read while the chat is open. */
export function useDirectLineRun(directorId: string | null): ProjectRun | null {
  const { data } = useQuery({
    queryKey: ["slim-direct-line", directorId],
    queryFn: async ({ signal }) => {
      const res = await authenticatedFetch(
        `/v1/slim/directors/${encodeURIComponent(directorId ?? "")}`,
        { signal },
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return parseDirectLine(await res.json());
    },
    enabled: Boolean(directorId),
    refetchInterval: REFRESH_MS,
    placeholderData: (previous, previousQuery) =>
      previousQuery?.queryKey[1] === directorId ? previous : undefined,
    retry: false,
  });
  return data ?? null;
}

// ── Who the person is talking to ────────────────────────────────────────────

export type LineTarget = "thread" | "aviator";

interface LiveLine {
  threadId: string;
  /** The agent the thread runs, once its session has loaded. */
  agentId: string | null;
}

// Kept outside React so the send path can read it without a hook: the line
// each open director chat has, and which end the person chose to talk to.
const liveLines = new Map<string, LiveLine>();
const chosenTargets = new Map<string, LineTarget>();
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Record (or clear, with null) the thread a director's chat has a line to. */
export function registerDirectLine(directorId: string, line: LiveLine | null): void {
  const current = liveLines.get(directorId);
  if (line === null) {
    if (current === undefined) return;
    liveLines.delete(directorId);
    chosenTargets.delete(directorId);
  } else {
    if (current?.threadId === line.threadId && current.agentId === line.agentId) return;
    // A new thread takes the floor: the person talks to it until they say otherwise.
    if (current?.threadId !== line.threadId) chosenTargets.delete(directorId);
    liveLines.set(directorId, line);
  }
  emit();
}

export function setLineTarget(directorId: string, target: LineTarget): void {
  if ((chosenTargets.get(directorId) ?? "thread") === target) return;
  chosenTargets.set(directorId, target);
  emit();
}

/** Who the message box sends to in this director's chat. */
export function useLineTarget(directorId: string | null): LineTarget {
  return useSyncExternalStore(subscribe, () =>
    directorId === null ? "thread" : (chosenTargets.get(directorId) ?? "thread"),
  );
}

const AVIATOR_MENTION = /^\s*@aviator\b[\s,:]*/i;

export interface LineRoute {
  /** The thread to send to, or null for the director itself. */
  threadId: string | null;
  agentId: string | null;
  /** The message, without a leading `@aviator`. */
  text: string;
}

/**
 * Where a message typed in a director's chat goes.
 *
 * To the thread with the floor, unless the person switched to Aviator or
 * began the message with `@aviator` (which is then removed).
 */
export function routeLineMessage(directorId: string | null, text: string): LineRoute {
  const line = directorId === null ? undefined : liveLines.get(directorId);
  if (line === undefined) return { threadId: null, agentId: null, text };
  if (AVIATOR_MENTION.test(text)) {
    const rest = text.replace(AVIATOR_MENTION, "");
    // "@aviator" alone is still a message to Aviator.
    return { threadId: null, agentId: null, text: rest.trim() ? rest : text };
  }
  if ((chosenTargets.get(directorId!) ?? "thread") === "aviator") {
    return { threadId: null, agentId: null, text };
  }
  return { threadId: line.threadId, agentId: line.agentId, text };
}

/** What Pause on the strip sends to the thread: the agent writes the note (D-93). */
export const PAUSE_MESSAGE = "Pause here. Note where we are so I can pick this up later.";

// ── The thread's turns, in the director's transcript ────────────────────────

function stampOf(bubble: Bubble): number | undefined {
  const stamp = (bubble as { createdAtS?: number }).createdAtS;
  return typeof stamp === "number" && stamp > 0 ? stamp : undefined;
}

/**
 * The director's own bubbles and the thread's, in the order they happened.
 *
 * Each list keeps its own order. A bubble with no time stamp stays with the
 * one before it; thread bubbles with no stamp at all go last, where a turn
 * still being written belongs. On a tie the director's bubble comes first.
 */
export function mergeLineBubbles(own: readonly Bubble[], line: readonly Bubble[]): Bubble[] {
  if (line.length === 0) return own as Bubble[];
  const times = (list: readonly Bubble[], start: number): number[] => {
    let last = start;
    return list.map((bubble) => {
      // Never step back: a late stamp inside a list must not reorder it.
      last = Math.max(last, stampOf(bubble) ?? last);
      return last;
    });
  };
  const ownTimes = times(own, 0);
  const lineTimes = times(line, stampOf(line[0]!) === undefined ? Number.POSITIVE_INFINITY : 0);
  const merged: Bubble[] = [];
  let i = 0;
  let j = 0;
  while (i < own.length || j < line.length) {
    if (j >= line.length || (i < own.length && ownTimes[i]! <= lineTimes[j]!)) {
      merged.push(own[i++]!);
    } else {
      merged.push(line[j++]!);
    }
  }
  return merged;
}
