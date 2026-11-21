// omnigent-slim: what a project is and what it touches (D-97, D-119).
//
// A project is one in-market goal inside an area. Its connections are typed
// links that hang from specific records (a requirement handed to another
// team is that team's project), so they are not a family tree. The server
// groups them at `GET /v1/slim/projects/connections`; a link stored on one
// project's record is read the other way from the far end.

import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/identity";

export const PROJECT_STATES = [
  "shaping",
  "in-delivery",
  "shipped",
  "slipped",
  "paused",
  "stopped",
] as const;
export type ProjectState = (typeof PROJECT_STATES)[number];

export const PROJECT_STATE_LABELS: Record<ProjectState, string> = {
  shaping: "Shaping",
  "in-delivery": "In delivery",
  shipped: "Shipped",
  slipped: "Slipped",
  paused: "Paused",
  stopped: "Stopped",
};

export interface ProjectCard {
  name: string;
  goal: string;
  area: string;
  /** Who runs it, when it is another team's. */
  team: string;
  state: ProjectState | null;
  /** A few words on the state, e.g. "slipped 2 wks". */
  stateNote: string;
}

export interface Connection {
  /** The record the link hangs from. */
  item: { id: string; title: string; data: string };
  /** The project at the other end; null when the record's dataset names none. */
  project: ProjectCard | null;
}

export interface ProjectConnections {
  /** Null when nobody has written what this project is yet. */
  project: ProjectCard | null;
  livesIn: string | null;
  cameFrom: Connection[];
  handedTo: Connection[];
  reliesOn: Connection[];
  reliedOnBy: Connection[];
}

const text = (value: unknown): string => (typeof value === "string" ? value.trim() : "");

function parseCard(raw: unknown): ProjectCard | null {
  if (typeof raw !== "object" || raw === null) return null;
  const data = raw as Record<string, unknown>;
  const name = text(data.name);
  if (!name) return null;
  const state = text(data.state);
  return {
    name,
    goal: text(data.goal),
    area: text(data.area),
    team: text(data.team),
    state: (PROJECT_STATES as readonly string[]).includes(state) ? (state as ProjectState) : null,
    stateNote: text(data.state_note),
  };
}

function parseGroup(raw: unknown): Connection[] {
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((entry): Connection[] => {
    if (typeof entry !== "object" || entry === null) return [];
    const item = (entry as { item?: unknown }).item;
    if (typeof item !== "object" || item === null) return [];
    const data = item as Record<string, unknown>;
    const id = text(data.id);
    if (!id) return [];
    return [
      {
        item: { id, title: text(data.title), data: text(data.data) },
        project: parseCard((entry as { project?: unknown }).project),
      },
    ];
  });
}

/** Read the `GET /v1/slim/projects/connections` answer. */
export function parseProjectConnections(raw: unknown): ProjectConnections {
  const data = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
  return {
    project: parseCard(data.project),
    livesIn: text(data.lives_in) || null,
    cameFrom: parseGroup(data.came_from),
    handedTo: parseGroup(data.handed_to),
    reliesOn: parseGroup(data.relies_on),
    reliedOnBy: parseGroup(data.relied_on_by),
  };
}

/** Whether there is anything to show: a described project, or any link. */
export function hasConnections(c: ProjectConnections): boolean {
  return (
    c.project !== null ||
    c.cameFrom.length + c.handedTo.length + c.reliesOn.length + c.reliedOnBy.length > 0
  );
}

/** "Slipped 2 wks" when the state has a note, else "Slipped"; "" with no state. */
export function projectStateText(card: ProjectCard): string {
  if (card.state === null) return "";
  return card.stateNote
    ? card.stateNote.charAt(0).toUpperCase() + card.stateNote.slice(1)
    : PROJECT_STATE_LABELS[card.state];
}

export function useProjectConnections(projectName: string) {
  return useQuery<ProjectConnections>({
    queryKey: ["slim-project-connections", projectName],
    queryFn: async ({ signal }) => {
      const res = await authenticatedFetch(
        `/v1/slim/projects/connections?project=${encodeURIComponent(projectName)}`,
        { signal },
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return parseProjectConnections(await res.json());
    },
    enabled: Boolean(projectName),
    refetchInterval: 15000,
    retry: false,
  });
}
