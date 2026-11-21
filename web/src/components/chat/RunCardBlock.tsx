// omnigent-slim: the live card for a workflow running in a thread, drawn in
// the director's chat (see lib/runBlock.ts).
//
// Intent: the person stays with the director (D-89) and still sees where each
// piece of work is: its step, whether it needs them, and the last thing the
// thread chose to report (D-118). The card is the way into the thread until
// the direct line (D-116) carries the conversation here.

import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/identity";
import { Link } from "@/lib/routing";
import { type RunBlock, runIdOfFile } from "@/lib/runBlock";
import { cn } from "@/lib/utils";
import { parseProjectRun, type ProjectRun, runStepLine } from "@/projectHome/projectRuns";
import { RunStateChip, RunStepsBar } from "@/projectHome/RunParts";
import { useChatStore } from "@/store/chatStore";

const REFRESH_MS = 5000;
const SHOWN_REPORTS = 3;

/** The run in `file`, re-read while the card is on screen; null until the thread writes it. */
function useRunFile(conversationId: string | null, file: string): ProjectRun | null {
  const { data } = useQuery({
    queryKey: ["slim-run-card", conversationId, file],
    queryFn: async ({ signal }) => {
      // Through the server, not the session's files: an old director session
      // has no runner to read files with, and the card should still fill in.
      const res = await authenticatedFetch(
        `/v1/slim/runs/${encodeURIComponent(runIdOfFile(file))}?session=${encodeURIComponent(conversationId ?? "")}`,
        { signal },
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const body = (await res.json()) as { run?: unknown };
      // Null until the thread has written its first step.
      return parseProjectRun(body.run);
    },
    enabled: Boolean(conversationId),
    refetchInterval: REFRESH_MS,
    placeholderData: (previous) => previous,
    retry: false,
  });
  return data ?? null;
}

export function RunCardBlock({ block }: { block: RunBlock }) {
  const conversationId = useChatStore((s) => s.conversationId);
  const run = useRunFile(conversationId, block.file);
  const threadId = run?.session ?? block.sessionId;
  // A run working in this very session needs no way in.
  const elsewhere = threadId !== null && threadId !== conversationId;
  const needsYou = run?.state === "needs-you";
  const note = run ? (run.state === "paused" ? run.leftOff : run.note) : "";
  const reports = run ? run.reports.slice(-SHOWN_REPORTS) : [];
  return (
    <div
      data-testid="run-card"
      data-state={run?.state ?? "starting"}
      className={cn(
        "not-prose my-2 flex flex-col gap-2 rounded-[var(--pa-r-panel)] border bg-[var(--pa-surface)] p-3 text-[13px]",
        needsYou ? "border-[var(--pa-attn)]" : "border-[var(--pa-line)]",
      )}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          {run ? (
            <>
              <p className="truncate text-[11px] font-semibold text-[var(--pa-ink-3)]">
                {run.workflow} · in its own thread
              </p>
              <p className="truncate text-[14px] font-semibold text-[var(--pa-ink)]">
                {run.subject || run.workflow}
              </p>
            </>
          ) : (
            <p className="truncate text-[14px] font-semibold text-[var(--pa-ink)]">
              {block.title ?? "Starting a thread"}
            </p>
          )}
        </div>
        {run ? (
          <RunStateChip state={run.state} />
        ) : (
          <span className="shrink-0 rounded-full bg-[var(--pa-agent-soft)] px-2 py-0.5 text-[11px] leading-4 font-semibold text-[var(--pa-agent)]">
            Starting
          </span>
        )}
      </div>
      {run && (
        <div className="flex flex-col gap-1">
          <RunStepsBar run={run} />
          <p className="truncate text-[var(--pa-ink-2)]">{runStepLine(run)}</p>
        </div>
      )}
      {note && (
        <p className="text-[var(--pa-ink-2)]">
          <span className="block text-[11px] font-semibold text-[var(--pa-ink-3)]">
            {run?.state === "paused" ? "Where you left off" : needsYou ? "Needs from you" : "Now"}
          </span>
          {note}
        </p>
      )}
      {reports.length > 0 && (
        <ul className="flex flex-col gap-0.5 border-t border-[var(--pa-line)] pt-2">
          {reports.map((report) => (
            <li key={`${report.at}:${report.text}`} className="flex gap-2 text-[var(--pa-ink-2)]">
              <span
                aria-hidden="true"
                className={cn(
                  "mt-[7px] size-1.5 shrink-0 rounded-full",
                  report.kind === "blocker"
                    ? "bg-[var(--pa-attn)]"
                    : report.kind === "done"
                      ? "bg-[var(--pa-ok)]"
                      : "bg-[var(--pa-agent)]",
                )}
              />
              <span className="min-w-0 flex-1">
                {report.kind === "blocker" && <span className="font-semibold">Blocked: </span>}
                {report.text}
              </span>
            </li>
          ))}
        </ul>
      )}
      {!run && (
        <p className="text-[var(--pa-ink-3)]">The thread is reading its brief. This card fills in as it works.</p>
      )}
      {elsewhere && (
        <div className="flex justify-end">
          <Link
            to={`/c/${threadId}`}
            className={cn(
              "rounded-[var(--pa-r)] px-2.5 py-1 text-[13px] font-medium no-underline outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--pa-navy)]",
              needsYou || run?.state === "paused"
                ? "bg-[var(--pa-navy)] text-[var(--pa-on-navy)] hover:bg-[var(--pa-navy-hover)]"
                : "border border-[var(--pa-line-strong)] text-[var(--pa-ink)] hover:bg-[var(--pa-sunk)]",
            )}
          >
            {needsYou ? "Answer in the thread" : "Open the thread"}
          </Link>
        </div>
      )}
    </div>
  );
}
