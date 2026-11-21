import { afterEach, describe, expect, it } from "vitest";
import type { Bubble } from "@/lib/renderItems";
import {
  mergeLineBubbles,
  parseDirectLine,
  registerDirectLine,
  routeLineMessage,
  setLineTarget,
} from "./directLine";

const user = (itemId: string, createdAtS?: number): Bubble =>
  ({ kind: "user", itemId, content: [], createdAtS }) as Bubble;
const ids = (bubbles: Bubble[]) => bubbles.map((b) => (b as { itemId: string }).itemId);

describe("the direct line to a thread (D-116)", () => {
  afterEach(() => registerDirectLine("d1", null));

  it("reads the run with the floor, and only when it has a thread", () => {
    const run = { id: "r", workflow: "W", steps: ["One"], current: 1, state: "working" };
    expect(parseDirectLine({ line: { ...run, session: "t1" } })?.session).toBe("t1");
    expect(parseDirectLine({ line: run })).toBeNull();
    expect(parseDirectLine({ line: null })).toBeNull();
  });

  it("sends to the director when no thread has the floor", () => {
    expect(routeLineMessage("d1", "hello")).toEqual({ threadId: null, agentId: null, text: "hello" });
  });

  it("sends straight to the thread while it has the floor", () => {
    registerDirectLine("d1", { threadId: "t1", agentId: "a1" });
    expect(routeLineMessage("d1", "Weekly savers.")).toEqual({
      threadId: "t1",
      agentId: "a1",
      text: "Weekly savers.",
    });
  });

  it("sends an @aviator message to Aviator, without the mention", () => {
    registerDirectLine("d1", { threadId: "t1", agentId: "a1" });
    expect(routeLineMessage("d1", "@Aviator, what else is in flight?")).toEqual({
      threadId: null,
      agentId: null,
      text: "what else is in flight?",
    });
    // The mention only counts at the start.
    expect(routeLineMessage("d1", "ask @aviator later").threadId).toBe("t1");
  });

  it("keeps sending to Aviator once the person switches, until a new thread takes the floor", () => {
    registerDirectLine("d1", { threadId: "t1", agentId: "a1" });
    setLineTarget("d1", "aviator");
    expect(routeLineMessage("d1", "hello").threadId).toBeNull();
    registerDirectLine("d1", { threadId: "t2", agentId: "a1" });
    expect(routeLineMessage("d1", "hello").threadId).toBe("t2");
  });

  it("orders the director's turns and the thread's by when they happened", () => {
    const own = [user("d-1", 10), user("d-2", 40)];
    const line = [user("t-1", 20), user("t-2"), user("t-3", 50)];
    expect(ids(mergeLineBubbles(own, line))).toEqual(["d-1", "t-1", "t-2", "d-2", "t-3"]);
  });

  it("puts a thread turn with no time yet last, and leaves a chat with no thread alone", () => {
    const own = [user("d-1", 10)];
    expect(ids(mergeLineBubbles(own, [user("t-live")]))).toEqual(["d-1", "t-live"]);
    expect(mergeLineBubbles(own, [])).toBe(own);
  });
});
