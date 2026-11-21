import { describe, expect, it } from "vitest";
import { hasConnections, parseProjectConnections, projectStateText } from "./projectConnections";

describe("a project's goal and connections (D-97, D-119)", () => {
  it("reads the project and its links by what they mean", () => {
    const c = parseProjectConnections({
      project: { name: "Held payments clarity", goal: "Know when money arrives", area: "Held payments" },
      lives_in: "Held payments",
      handed_to: [
        {
          item: { id: "R-07", title: "Alerts", data: "data/reqs.json" },
          project: { name: "Hold alerts", team: "Cards Platform", state: "slipped", state_note: "slipped 2 wks" },
        },
        { item: {}, project: null },
      ],
      came_from: [{ item: { id: "P-2", title: "No idea when" }, project: null }],
    });
    expect(c.project?.goal).toBe("Know when money arrives");
    expect(c.livesIn).toBe("Held payments");
    expect(c.handedTo).toHaveLength(1);
    expect(c.handedTo[0].project?.state).toBe("slipped");
    expect(projectStateText(c.handedTo[0].project!)).toBe("Slipped 2 wks");
    expect(c.cameFrom[0].project).toBeNull();
    expect(hasConnections(c)).toBe(true);
  });

  it("has nothing to show for a project nobody has described or linked", () => {
    const c = parseProjectConnections({ project: null });
    expect(hasConnections(c)).toBe(false);
    expect(parseProjectConnections("junk").handedTo).toEqual([]);
  });

  it("ignores a state it does not know", () => {
    const c = parseProjectConnections({ project: { name: "X", state: "on fire" } });
    expect(c.project?.state).toBeNull();
    expect(projectStateText(c.project!)).toBe("");
  });
});
