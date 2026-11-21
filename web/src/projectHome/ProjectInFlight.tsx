// omnigent-slim: the "In flight" section of a project's page (D-96).
//
// One card per run: the workflow, its subject, the step it is on, its state,
// where it was left, and a way back in. It sits above the sessions board
// because the question a person brings to this page is "what was I in the
// middle of", and a run can outlive the session it started in.

import { useState } from "react";
import { useNavigate } from "@/lib/routing";
import { HANGAR_WRENCH_GROUP, HangarWrench } from "@/hangar/HangarWrench";
import { hangarPath } from "@/hangar/hangarApi";
import { setPendingPrompt } from "@/lib/pendingPrompt";
import { cn } from "@/lib/utils";
import { formatAge } from "@/shell/SessionOverviewFiles";
import {
  isInFlight,
  type ProjectRun,
  resumeMessage,
  RUN_STATE_LABELS,
  runStepLine,
  useProjectRuns,
} from "./projectRuns";
import { RunStateChip, RunStepsBar } from "./RunParts";

const BUTTON =
  "rounded-[var(--pa-r)] px-2.5 py-1 text-[13px] font-medium outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--pa-navy)]";

function age(run: ProjectRun): string {
  const at = Date.parse(run.updated);
  return Number.isFinite(at) ? formatAge(at / 1000) : "";
}

/** Where pressing the card's button goes, and what it leaves in the message box. */
function useOpenRun(projectName: string) {
  const navigate = useNavigate();
  return (run: ProjectRun, resume: boolean) => {
    if (run.session) {
      if (resume) setPendingPrompt(run.session, resumeMessage(run));
      navigate(`/c/${run.session}`);
      return;
    }
    // Its session is gone: the run carries on in a new one.
    const params = new URLSearchParams({ project: projectName, prompt: resumeMessage(run) });
    navigate(`/?${params.toString()}`);
  };
}

function RunCard({ run, onOpen }: { run: ProjectRun; onOpen: (resume: boolean) => void }) {
  const resumes = run.state === "paused" || run.session === null;
  const noteLabel =
    run.state === "paused" ? "Where you left off" : run.state === "needs-you" ? "Needs from you" : "";
  const note = run.state === "paused" ? run.leftOff : run.note;
  const when = age(run);
  return (
    <article
      data-testid="project-run"
      data-state={run.state}
      aria-label={`${run.workflow}${run.subject ? `, ${run.subject}` : ""}: ${RUN_STATE_LABELS[run.state]}`}
      className={cn(
        "flex w-80 max-w-[85vw] shrink-0 flex-col gap-2 rounded-[var(--pa-r-panel)] border bg-[var(--pa-surface)] p-3 text-[13px]",
        run.state === "needs-you" ? "border-[var(--pa-attn)]" : "border-[var(--pa-line)]",
        HANGAR_WRENCH_GROUP,
      )}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[11px] font-semibold text-[var(--pa-ink-3)]">
            {run.workflow}
          </p>
          <p className="truncate text-[14px] font-semibold text-[var(--pa-ink)]">
            {run.subject || run.workflow}
          </p>
        </div>
        {run.scenario && (
          <HangarWrench
            to={hangarPath.workflow(run.scenario)}
            label={`Open ${run.workflow} in the Hangar`}
          />
        )}
        <RunStateChip state={run.state} />
      </div>
      <div className="flex flex-col gap-1">
        <RunStepsBar run={run} />
        <p className="truncate text-[var(--pa-ink-2)]">{runStepLine(run)}</p>
      </div>
      {note && (
        <p className="line-clamp-3 text-[var(--pa-ink-2)]">
          {noteLabel && (
            <span className="block text-[11px] font-semibold text-[var(--pa-ink-3)]">{noteLabel}</span>
          )}
          {note}
        </p>
      )}
      {!note && run.reports.length > 0 && (
        <p className="line-clamp-2 text-[var(--pa-ink-2)]">{run.reports[run.reports.length - 1].text}</p>
      )}
      {run.counts && (
        <p className="text-[12px] text-[var(--pa-ink-3)]">
          {run.counts.done} of {run.counts.total} {run.counts.noun} {run.counts.label}
          {run.counts.waiting > 0 && ` · ${run.counts.waiting} waiting on you`}
        </p>
      )}
      <div className="mt-auto flex items-center gap-2 pt-1">
        <span className="min-w-0 flex-1 truncate text-[12px] text-[var(--pa-ink-3)]">
          {when}
          {run.session === null && (when ? " · session closed" : "Session closed")}
        </span>
        <button
          type="button"
          onClick={() => onOpen(resumes)}
          className={cn(
            BUTTON,
            resumes || run.state === "needs-you"
              ? "bg-[var(--pa-navy)] text-[var(--pa-on-navy)] hover:bg-[var(--pa-navy-hover)]"
              : "border border-[var(--pa-line-strong)] text-[var(--pa-ink)] hover:bg-[var(--pa-sunk)]",
          )}
        >
          {resumes ? "Resume" : run.state === "needs-you" ? "Answer" : "Open"}
        </button>
      </div>
    </article>
  );
}

/**
 * The project's runs. Draws nothing when the project has never had a run, so a
 * project used only for plain sessions looks as it did.
 */
export function ProjectInFlight({ projectName }: { projectName: string }) {
  const { data } = useProjectRuns(projectName);
  const open = useOpenRun(projectName);
  const [showPast, setShowPast] = useState(false);
  const runs = data?.runs ?? [];
  if (runs.length === 0) return null;
  const inFlight = runs.filter(isInFlight);
  const past = runs.filter((run) => !isInFlight(run));
  const needsYou = data?.needsYou ?? 0;
  return (
    <section
      aria-label="In flight"
      data-testid="project-in-flight"
      className="flex shrink-0 flex-col gap-2 px-4 pt-1 pb-3 font-[family-name:var(--pa-font)]"
    >
      <div className="flex items-baseline gap-2">
        <h2 className="text-[13px] font-semibold text-[var(--pa-ink)]">In flight</h2>
        <span className="text-[12px] text-[var(--pa-ink-3)]">
          {inFlight.length === 0
            ? "Nothing in flight"
            : `${inFlight.length} ${inFlight.length === 1 ? "run" : "runs"}`}
          {needsYou > 0 && (
            <span className="font-semibold text-[var(--pa-attn)]">
              {" "}
              · {needsYou} {needsYou === 1 ? "needs" : "need"} you
            </span>
          )}
        </span>
        {past.length > 0 && (
          <button
            type="button"
            aria-expanded={showPast}
            onClick={() => setShowPast((shown) => !shown)}
            className="ml-auto text-[12px] text-[var(--pa-ink-3)] underline-offset-2 outline-none hover:text-[var(--pa-ink)] hover:underline focus-visible:underline"
          >
            {showPast ? "Hide" : "Show"} {past.length} finished or stopped
          </button>
        )}
      </div>
      {inFlight.length > 0 && (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {inFlight.map((run) => (
            <RunCard key={run.id} run={run} onOpen={(resume) => open(run, resume)} />
          ))}
        </div>
      )}
      {showPast && (
        <ul className="flex flex-col gap-1" data-testid="project-past-runs">
          {past.map((run) => (
            <li key={run.id} className="flex items-center gap-2 text-[13px] text-[var(--pa-ink-2)]">
              <RunStateChip state={run.state} />
              <span className="min-w-0 flex-1 truncate">
                <span className="font-medium text-[var(--pa-ink)]">{run.workflow}</span>
                {run.subject && ` · ${run.subject}`}
                {run.state === "stopped" && ` · ${runStepLine(run)}`}
              </span>
              <span className="shrink-0 text-[12px] text-[var(--pa-ink-3)]">{age(run)}</span>
              <button
                type="button"
                onClick={() => open(run, run.state === "stopped")}
                className={cn(BUTTON, "text-[var(--pa-ink)] hover:bg-[var(--pa-sunk)]")}
              >
                {run.state === "stopped" ? "Resume" : "Open"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
