import { describe, expect, it } from "vitest";
import { othersLabel, parseThreadContext } from "./threadContext";

const run = (id: string, state: string, session: string) => ({
  id,
  workflow: "Intent shaping",
  subject: id,
  steps: ["One", "Two"],
  current: 1,
  state,
  session,
});

describe("a thread's page and its folded director (D-117)", () => {
  it("reads the director, this thread's run and what else is in flight", () => {
    const context = parseThreadContext({
      thread: {
        director: { id: "d1", title: " Teen allowances " },
        run: run("mine", "working", "t1"),
        others: [run("a", "needs-you", "t2"), run("b", "paused", "t3"), "junk"],
      },
    });
    expect(context?.director).toEqual({ id: "d1", title: "Teen allowances" });
    expect(context?.run?.id).toBe("mine");
    expect(context?.others.map((r) => r.id)).toEqual(["a", "b"]);
    expect(context?.needsYou).toBe(1);
  });

  it("is a thread before its run file exists", () => {
    const context = parseThreadContext({ thread: { director: { id: "d1", title: "" }, run: null } });
    expect(context).toMatchObject({ run: null, others: [], needsYou: 0 });
  });

  it("is nothing for a session that is not a thread", () => {
    expect(parseThreadContext({ thread: null })).toBeNull();
    expect(parseThreadContext({ thread: { director: {} } })).toBeNull();
    expect(parseThreadContext("nope")).toBeNull();
  });

  it("counts the others in the person's words", () => {
    expect(othersLabel(0)).toBe("");
    expect(othersLabel(1)).toBe("1 other in flight");
    expect(othersLabel(3)).toBe("3 others in flight");
  });
});
