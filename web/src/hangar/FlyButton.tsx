/**
 * omnigent-slim: "Fly this" (D-76 to D-81). A scenario you build, a demo you fly.
 *
 * Flying makes (or reuses) the scenario's "◆ Demo · <title>" project and opens a
 * new session there with the opening line in the composer. If the demo was
 * flown before, the person chooses "Reset to the start" or "Keep going".
 * The Library's Demos entries use the same route and the same component.
 */

import { useState } from "react";
import { useNavigate } from "@/lib/routing";
import { type DemoInfo, demoSessionLink, useFlyScenario } from "./hangarApi";
import { ActionError } from "./parts";

export function FlyButton({
  scenarioId,
  demo,
  disabled,
  label = "Fly this",
  liveTurns,
}: {
  scenarioId: string;
  /** False plays every turn canned; undefined keeps the script's live turns (or what was set before). */
  liveTurns?: boolean;
  /** The demo as the catalog last saw it, so the choice can show without a round trip. */
  demo?: DemoInfo | null;
  disabled?: boolean;
  label?: string;
}) {
  const fly = useFlyScenario();
  const navigate = useNavigate();
  const [existing, setExisting] = useState<DemoInfo | null>(null);

  const go = async (mode?: "reset" | "keep") => {
    const result = await fly.mutateAsync({ id: scenarioId, mode, liveTurns });
    if (result.state === "exists") {
      setExisting(result.demo);
      return;
    }
    setExisting(null);
    navigate(demoSessionLink(result));
  };

  const start = () => {
    if (demo) setExisting(demo);
    else void go().catch(() => undefined);
  };

  return (
    <div className="flybox" data-testid="hangar-fly">
      {existing ? (
        <div className="flychoice" role="group" aria-label="This demo has been flown before">
          <span className="lab">
            Flown before ·{" "}
            {existing.finished
              ? "played to the end"
              : existing.turn
                ? `turn ${existing.turn} of ${existing.turns}`
                : "not started yet"}
          </span>
          <button
            type="button"
            className="hangar-btn pri"
            disabled={fly.isPending}
            onClick={() => void go("reset").catch(() => undefined)}
          >
            Reset to the start
          </button>
          <button
            type="button"
            className="hangar-btn"
            disabled={fly.isPending}
            onClick={() => void go("keep").catch(() => undefined)}
          >
            Keep going
          </button>
          <button type="button" className="hangar-btn quiet" onClick={() => setExisting(null)}>
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="hangar-btn pri fly"
          disabled={disabled || fly.isPending}
          onClick={start}
          title="Open a ◆ Demo project with a real session that plays this scenario"
        >
          ◆ {fly.isPending ? "Getting the demo ready…" : label}
        </button>
      )}
      <ActionError error={fly.error} />
    </div>
  );
}

export function demoNote(demo: DemoInfo | null | undefined): string {
  if (!demo) return "Plays in a ◆ Demo project, in a real session.";
  return `In the project “${demo.project}”.`;
}
