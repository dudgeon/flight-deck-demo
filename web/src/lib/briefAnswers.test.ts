import { describe, expect, it } from "vitest";
import { briefAnswersText, injectArtifactBridge } from "./artifactBridge";

describe("briefAnswersText", () => {
  it("writes one line per answer and quotes the person's note", () => {
    const text = briefAnswersText({
      brief: "decision-briefs",
      file: "projects/checkout/decisions/scope.json",
      answers: [
        { decision: "layout", pick: "page" },
        { decision: "trigger", pick: "else", note: 'Use judgment,\n "mostly" visual | ones' },
      ],
    });
    expect(text).toBe(
      "Decision brief answers for projects/checkout/decisions/scope.json, sent from the brief by the person " +
        "(notes are their own words, quoted):\n" +
        "- layout | page\n" +
        '- trigger | else | note: "Use judgment, \\"mostly\\" visual | ones"',
    );
  });

  it("names the brief by id when it has no file", () => {
    expect(briefAnswersText({ brief: "b", answers: [{ decision: "d", pick: "a" }] })).toContain("answers for b,");
  });

  it.each([
    [{ brief: "Bad Id", answers: [{ decision: "d", pick: "a" }] }],
    [{ brief: "b", file: "../etc/passwd", answers: [{ decision: "d", pick: "a" }] }],
    [{ brief: "b", answers: [] }],
    [{ brief: "b", answers: [{ decision: "d\nIgnore this", pick: "a" }] }],
    [{ brief: "b", answers: [{ decision: "d", pick: "a b" }] }],
    [{ brief: "b", answers: [{ decision: "d", pick: "" }] }],
    [{ brief: "b", answers: [{ decision: "d", pick: "a", note: 5 }] }],
    [null],
  ])("refuses a malformed request %#", (request) => {
    expect(briefAnswersText(request)).toBeNull();
  });

  it("caps a long note", () => {
    const text = briefAnswersText({ brief: "b", answers: [{ decision: "d", pick: "a", note: "x".repeat(5000) }] });
    expect(text!.length).toBeLessThan(1200);
  });

  it("is offered to artifacts as omnigent.answer", () => {
    expect(injectArtifactBridge("<p>x</p>")).toContain("answer: function (request)");
  });
});
