// omnigent-slim: the director, folded to a bar on top of a thread (D-117).
//
// Intent: stepping into a thread is a choice to focus, so the thread takes the
// chat's place and the canvas keeps its room. The director does not vanish:
// it folds to this one line, which leads back to it, says where this thread's
// run is, and shows what else is in flight (amber only when something needs
// the person). Opening the list is the one place the rest of the project
// shows while focused.

import { ArrowLeftIcon, ChevronDownIcon } from "lucide-react";
import { useState } from "react";
import { Link } from "@/lib/routing";
import { othersLabel, useThreadContext } from "@/lib/threadContext";
import { cn } from "@/lib/utils";
import { runStepLine } from "@/projectHome/projectRuns";
import { RunStateChip } from "@/projectHome/RunParts";

const FOCUS =
  "outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--pa-navy)]";

export function DirectorBar({ conversationId }: { conversationId: string | null }) {
  const context = useThreadContext(conversationId);
  const [open, setOpen] = useState(false);
  if (!context) return null;
  const { director, run, others, needsYou } = context;
  const label = othersLabel(others.length);
  return (
    <div
      data-testid="director-bar"
      className="pa-director-bar shrink-0 border-b border-[var(--pa-line)] bg-[var(--pa-sunk)] text-[13px]"
    >
      <div className="flex min-h-9 items-center gap-2 px-3 py-1.5">
        <Link
          to={`/c/${director.id}`}
          title="Back to the director"
          className={cn(
            "flex min-w-0 shrink items-center gap-1.5 rounded-[var(--pa-r)] px-1.5 py-0.5 font-medium text-[var(--pa-ink)] no-underline hover:bg-[var(--pa-surface)]",
            FOCUS,
          )}
        >
          <ArrowLeftIcon aria-hidden="true" className="size-3.5 shrink-0" />
          <span className="truncate">{director.title || "Aviator"}</span>
        </Link>
        {run && (
          <>
            <span aria-hidden="true" className="text-[var(--pa-ink-3)]">
              ·
            </span>
            <span className="min-w-0 flex-1 truncate text-[var(--pa-ink-2)]">
              This thread: {run.subject || run.workflow} · {runStepLine(run)}
            </span>
            <RunStateChip state={run.state} />
          </>
        )}
        {!run && <span className="flex-1" />}
        {label && (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-[var(--pa-r)] px-1.5 py-0.5 text-[var(--pa-ink-2)] hover:bg-[var(--pa-surface)]",
              FOCUS,
            )}
          >
            {needsYou > 0 && (
              <span className="rounded-full bg-[var(--pa-attn-soft)] px-2 py-0.5 text-[11px] leading-4 font-semibold text-[var(--pa-attn)]">
                {needsYou === 1 ? "1 needs you" : `${needsYou} need you`}
              </span>
            )}
            <span>{label}</span>
            <ChevronDownIcon
              aria-hidden="true"
              className={cn("size-3.5 transition-transform", open && "rotate-180")}
            />
          </button>
        )}
      </div>
      {open && others.length > 0 && (
        <ul className="flex flex-col gap-0.5 border-t border-[var(--pa-line)] px-3 py-1.5">
          {others.map((other) => {
            const row = (
              <>
                <span className="min-w-0 flex-1 truncate">
                  <span className="font-medium text-[var(--pa-ink)]">
                    {other.subject || other.workflow}
                  </span>
                  <span className="text-[var(--pa-ink-3)]">
                    {" "}
                    · {other.workflow} · {runStepLine(other)}
                  </span>
                </span>
                <RunStateChip state={other.state} />
              </>
            );
            return (
              <li key={other.id}>
                {other.session ? (
                  <Link
                    to={`/c/${other.session}`}
                    className={cn(
                      "flex items-center gap-2 rounded-[var(--pa-r)] px-1.5 py-1 no-underline hover:bg-[var(--pa-surface)]",
                      FOCUS,
                    )}
                  >
                    {row}
                  </Link>
                ) : (
                  <div className="flex items-center gap-2 px-1.5 py-1">{row}</div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
