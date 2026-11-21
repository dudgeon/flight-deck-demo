import { describe, expect, it } from "vitest";
import {
  isInFlight,
  parseProjectRun,
  parseProjectRuns,
  resumeMessage,
  runStepLine,
} from "./projectRuns";

const RUN = {
  id: "allowances-intent--intent-shaping",
  workflow: "Intent shaping",
  scenario: "intent-shaping",
  subject: "Allowances",
  steps: ["Capture the idea", "Frame it", "Shape it"],
  current: 2,
  state: "paused",
  left_off: "Framed it; the metric is next.",
  data: "data/allowances-intent.json",
  session: "abc",
  session_title: "Allowances",
  updated: "2026-11-21T10:00:00+00:00",
};

describe("project runs (D-96)", () => {
  it("reads a paused run with its note and session", () => {
    const run = parseProjectRun(RUN)!;
    expect(run.state).toBe("paused");
    expect(run.leftOff).toBe("Framed it; the metric is next.");
    expect(run.session).toBe("abc");
    expect(runStepLine(run)).toBe("Step 2 of 3 · Frame it");
    expect(isInFlight(run)).toBe(true);
  });

  it("reads a file from before runs had a state", () => {
    expect(parseProjectRun({ ...RUN, state: undefined })!.state).toBe("working");
    const done = parseProjectRun({ ...RUN, state: "nonsense", current: 9 })!;
    expect(done.state).toBe("finished");
    expect(isInFlight(done)).toBe(false);
    expect(runStepLine(done)).toBe("Finished");
  });

  it("drops what is not a run", () => {
    expect(parseProjectRun({ ...RUN, steps: [] })).toBeNull();
    expect(parseProjectRun({ ...RUN, id: "" })).toBeNull();
    expect(parseProjectRun("nope")).toBeNull();
    expect(parseProjectRuns(null)).toEqual({ runs: [], needsYou: 0 });
  });

  it("counts the runs that need the person", () => {
    const all = parseProjectRuns({
      runs: [RUN, { ...RUN, id: "b", state: "needs-you" }, { ...RUN, id: "c", state: "needs-you" }],
    });
    expect(all.runs).toHaveLength(3);
    expect(all.needsYou).toBe(2);
  });

  it("writes a resume message that names the run and its data", () => {
    expect(resumeMessage(parseProjectRun(RUN)!)).toBe(
      'Resume intent shaping on "Allowances". Pick up where we left off. Its data is in data/allowances-intent.json.',
    );
    expect(resumeMessage(parseProjectRun({ ...RUN, subject: "", data: "" })!)).toBe(
      "Resume intent shaping. Pick up where we left off.",
    );
  });
});
