import { describe, expect, it } from "vitest";
import { parseProjectRun } from "@/projectHome/projectRuns";
import { parseRunBlock, runIdOfFile } from "./runBlock";

describe("run card block (D-89)", () => {
  it("reads the run's file, title and thread", () => {
    expect(
      parseRunBlock(
        "file: progress/teen-allowances-intent--intent-shaping.json\ntitle: Intent shaping: Teen allowances\nsession: 0123456789abcdef",
      ),
    ).toEqual({
      file: "progress/teen-allowances-intent--intent-shaping.json",
      title: "Intent shaping: Teen allowances",
      sessionId: "0123456789abcdef",
    });
    expect(runIdOfFile("progress/a--b.json")).toBe("a--b");
  });

  it("only draws progress files inside the workspace", () => {
    expect(parseRunBlock("file: ../secrets.json")).toBeNull();
    expect(parseRunBlock("file: progress/../../x.json")).toBeNull();
    expect(parseRunBlock("file: /etc/passwd")).toBeNull();
    expect(parseRunBlock("file: data/x.json")).toBeNull();
    expect(parseRunBlock("title: nothing")).toBeNull();
    expect(parseRunBlock("file: progress/x.json\nsession: no")?.sessionId).toBeNull();
  });

  it("reads a run's reports and drops what is not one", () => {
    const run = parseProjectRun({
      id: "a",
      steps: ["One"],
      director: "dir",
      reports: [{ kind: "blocker", text: "Stuck." }, { kind: "odd", text: "Fine." }, { text: "" }, 3],
    })!;
    expect(run.director).toBe("dir");
    expect(run.reports.map((r) => [r.kind, r.text])).toEqual([
      ["blocker", "Stuck."],
      ["milestone", "Fine."],
    ]);
  });
});
