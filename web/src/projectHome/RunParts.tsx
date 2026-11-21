// omnigent-slim: the small pieces every drawing of a run shares (the project
// page's In flight cards and the run card in the director's chat).

import { cn } from "@/lib/utils";
import { type ProjectRun, RUN_STATE_LABELS, type RunState } from "./projectRuns";

// Amber means "needs the person" and nothing else (D-50).
const CHIP: Record<RunState, string> = {
  "needs-you": "bg-[var(--pa-attn-soft)] text-[var(--pa-attn)]",
  paused: "bg-[var(--pa-idle-soft)] text-[var(--pa-ink-2)]",
  waiting: "bg-[var(--pa-info-soft)] text-[var(--pa-info)]",
  working: "bg-[var(--pa-agent-soft)] text-[var(--pa-agent)]",
  stopped: "bg-[var(--pa-idle-soft)] text-[var(--pa-ink-3)]",
  finished: "bg-[var(--pa-ok-soft)] text-[var(--pa-ok)]",
};

export function RunStateChip({ state }: { state: RunState }) {
  return (
    <span
      data-state={state}
      className={cn(
        "shrink-0 rounded-full px-2 py-0.5 text-[11px] leading-4 font-semibold",
        CHIP[state],
      )}
    >
      {RUN_STATE_LABELS[state]}
    </span>
  );
}

/** One segment per step: done, current, to do. */
export function RunStepsBar({ run }: { run: ProjectRun }) {
  return (
    <div className="flex gap-1" aria-hidden="true">
      {run.steps.map((step, index) => (
        <span
          key={step}
          className={cn(
            "h-1 flex-1 rounded-full",
            index + 1 < run.current
              ? "bg-[var(--pa-ok)]"
              : index + 1 === run.current
                ? "bg-[var(--pa-navy)]"
                : "bg-[var(--pa-line)]",
          )}
        />
      ))}
    </div>
  );
}
