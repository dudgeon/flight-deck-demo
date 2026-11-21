// omnigent-slim: participant messages in the Inbox (D-68 to D-70).
import { describe, expect, it } from "vitest";
import { participantMessageOf, type Suggestion } from "./proactiveInbox";

function suggestion(over: Partial<Suggestion>): Suggestion {
  return {
    id: "a".repeat(32),
    kind: "info",
    title: "t",
    bodyMd: "b",
    links: [],
    actions: [],
    media: [],
    sourceSessionId: "s1",
    agentId: "",
    status: "unread",
    resolution: "none",
    createdAt: 0,
    ...over,
  };
}

describe("participantMessageOf", () => {
  it("is null for an ordinary suggestion", () => {
    expect(participantMessageOf(suggestion({}))).toBeNull();
  });

  it("reads the sender, intent and session from the participant block", () => {
    const msg = participantMessageOf(
      suggestion({
        links: [{ type: "session", ref: "s2", label: "Allowances PRD" }],
        media: [
          {
            type: "participant",
            intent: "invite",
            participant: { id: "mara-okafor", name: "Mara Okafor", kind: "person", role: "Design", stand_in: true },
          },
        ],
      }),
    );
    expect(msg).toEqual({
      participant: { id: "mara-okafor", name: "Mara Okafor", kind: "person", role: "Design", standIn: true },
      intent: "invite",
      sessionId: "s2",
      sessionLabel: "Allowances PRD",
    });
  });

  it("falls back to the posting session and a plain message", () => {
    const msg = participantMessageOf(
      suggestion({ media: [{ type: "participant", participant: { id: "rr", name: "Risk Review", kind: "agent" } }] }),
    );
    expect(msg?.intent).toBe("message");
    expect(msg?.sessionId).toBe("s1");
    expect(msg?.participant.standIn).toBe(false);
  });
});
