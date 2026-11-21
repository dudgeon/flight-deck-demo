// omnigent-slim: the runs in flight in a project (D-96).
//
// A run is one workflow working on one subject. The agent keeps its state with
// `pa flow`; the server lists a project's runs at `GET /v1/slim/runs`. A run
// outlives its session, which is why the project page reads them here and not
// from any one session.

import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/identity";

export const RUN_STATES = [
  "needs-you",
  "paused",
  "waiting",
  "working",
  "stopped",
  "finished",
] as const;
export type RunState = (typeof RUN_STATES)[number];

export interface ProjectRun {
  /** The progress file's name without `.json`, e.g. `allowances-intent--intent-shaping`. */
  id: string;
  workflow: string;
  /** The workflow's folder id, for the Hangar link. */
  scenario: string;
  subject: string;
  steps: string[];
  /** 1-based; past the last step means finished. */
  current: number;
  state: RunState;
  /** What is happening in the current step. */
  note: string;
  /** The note the agent wrote when the person set the run aside. */
  leftOff: string;
  counts: { done: number; total: number; noun: string; label: string; waiting: number } | null;
  /** Workspace path of the run's dataset. */
  data: string;
  /** The session the run is in, when it still exists. */
  session: string | null;
  sessionTitle: string | null;
  /** ISO time of the last change. */
  updated: string;
}

export interface ProjectRuns {
  runs: ProjectRun[];
  needsYou: number;
}

const text = (value: unknown, max = 400): string =>
  typeof value === "string" ? value.slice(0, max) : "";
const whole = (value: unknown): number =>
  typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0;

/** Read one run from the server's JSON; `null` when it is not a run with steps. */
export function parseProjectRun(raw: unknown): ProjectRun | null {
  if (typeof raw !== "object" || raw === null) return null;
  const data = raw as Record<string, unknown>;
  const steps = Array.isArray(data.steps)
    ? data.steps.filter((step): step is string => typeof step === "string").slice(0, 12)
    : [];
  const id = text(data.id, 200);
  if (steps.length === 0 || !id) return null;
  const current = Math.min(steps.length + 1, Math.max(1, whole(data.current) || 1));
  const state = (RUN_STATES as readonly string[]).includes(text(data.state))
    ? (data.state as RunState)
    : current > steps.length
      ? "finished"
      : "working";
  const rawCounts =
    typeof data.counts === "object" && data.counts !== null
      ? (data.counts as Record<string, unknown>)
      : null;
  return {
    id,
    workflow: text(data.workflow, 120) || "Workflow",
    scenario: /^[a-z0-9][a-z0-9-]{0,80}$/.test(text(data.scenario)) ? text(data.scenario) : "",
    subject: text(data.subject, 160),
    steps,
    current,
    state,
    note: text(data.note),
    leftOff: text(data.left_off, 600),
    counts:
      rawCounts && whole(rawCounts.total) > 0
        ? {
            done: Math.min(whole(rawCounts.done), whole(rawCounts.total)),
            total: whole(rawCounts.total),
            noun: text(rawCounts.noun, 40) || "items",
            label: text(rawCounts.label, 40) || "done",
            waiting: whole(rawCounts.waiting),
          }
        : null,
    data: text(data.data, 300),
    session: text(data.session, 80) || null,
    sessionTitle: text(data.session_title, 200) || null,
    updated: text(data.updated, 40),
  };
}

/** Read the whole `GET /v1/slim/runs` answer. */
export function parseProjectRuns(raw: unknown): ProjectRuns {
  const list =
    typeof raw === "object" && raw !== null && Array.isArray((raw as { runs?: unknown }).runs)
      ? (raw as { runs: unknown[] }).runs
      : [];
  const runs = list.map(parseProjectRun).filter((run): run is ProjectRun => run !== null);
  return { runs, needsYou: runs.filter((run) => run.state === "needs-you").length };
}

/** Whether a run still belongs under "In flight" (finished and stopped ones are history). */
export function isInFlight(run: ProjectRun): boolean {
  return run.state !== "finished" && run.state !== "stopped";
}

export const RUN_STATE_LABELS: Record<RunState, string> = {
  "needs-you": "Needs you",
  paused: "Paused",
  waiting: "Waiting",
  working: "Working",
  stopped: "Stopped",
  finished: "Finished",
};

/** "Step 2 of 5 · Frame it", or "Finished". */
export function runStepLine(run: ProjectRun): string {
  if (run.current > run.steps.length) return "Finished";
  return `Step ${run.current} of ${run.steps.length} · ${run.steps[run.current - 1]}`;
}

/**
 * The message Resume puts in the message box. It names the run in the person's
 * words and the dataset, so the agent picks the same run up in any session.
 */
export function resumeMessage(run: ProjectRun): string {
  const what = run.subject
    ? `Resume ${run.workflow.toLowerCase()} on "${run.subject}".`
    : `Resume ${run.workflow.toLowerCase()}.`;
  const where = run.data ? ` Its data is in ${run.data}.` : "";
  return `${what} Pick up where we left off.${where}`;
}

/** A project's runs, refreshed while the page is open. */
export function useProjectRuns(projectName: string, { enabled = true } = {}) {
  return useQuery<ProjectRuns>({
    queryKey: ["slim-project-runs", projectName],
    queryFn: async ({ signal }) => {
      const res = await authenticatedFetch(
        `/v1/slim/runs?project=${encodeURIComponent(projectName)}`,
        { signal },
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return parseProjectRuns(await res.json());
    },
    enabled: enabled && projectName !== "",
    refetchInterval: 10_000,
    staleTime: 5_000,
    retry: false,
  });
}
