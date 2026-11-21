// omnigent-slim: the top of a project's page: its goal and its Connections
// card (D-97, D-119).
//
// Intent: a project is one goal that ships, so the page says the goal first.
// Its links to other work are specific (this requirement was handed to that
// team's project), so the card groups them by what the link means and names
// the item each hangs from. It answers "what does this project touch" without
// drawing a tree that is not there. Nothing shows until the project has been
// described or linked.

import { cn } from "@/lib/utils";
import {
  type Connection,
  hasConnections,
  type ProjectCard,
  type ProjectState,
  projectStateText,
  useProjectConnections,
} from "./projectConnections";

// Indigo is work moving, green done, amber what the person should look at (D-50).
const STATE_TONE: Record<ProjectState, string> = {
  shaping: "bg-[var(--pa-idle-soft)] text-[var(--pa-ink-2)]",
  "in-delivery": "bg-[var(--pa-agent-soft)] text-[var(--pa-agent)]",
  shipped: "bg-[var(--pa-ok-soft)] text-[var(--pa-ok)]",
  slipped: "bg-[var(--pa-attn-soft)] text-[var(--pa-attn)]",
  paused: "bg-[var(--pa-idle-soft)] text-[var(--pa-ink-2)]",
  stopped: "bg-[var(--pa-idle-soft)] text-[var(--pa-ink-3)]",
};

function StateChip({ card }: { card: ProjectCard }) {
  if (card.state === null) return null;
  return (
    <span
      data-state={card.state}
      className={cn(
        "shrink-0 rounded-full px-2 py-0.5 text-[11px] leading-4 font-semibold",
        STATE_TONE[card.state],
      )}
    >
      {projectStateText(card)}
    </span>
  );
}

function Row({ connection, away }: { connection: Connection; away: boolean }) {
  const { item, project } = connection;
  return (
    <li className="flex items-center gap-1.5">
      <span className="min-w-0 truncate text-[var(--pa-ink-2)]">
        <span className="font-medium text-[var(--pa-ink)]">{item.id}</span>
        {item.title && ` · ${item.title}`}
      </span>
      {project && (
        <>
          <span aria-hidden="true" className="shrink-0 text-[var(--pa-ink-3)]">
            {away ? "→" : "←"}
          </span>
          <span className="shrink-0 font-medium text-[var(--pa-ink)]">
            {project.name}
            {project.team && (
              <span className="font-normal text-[var(--pa-ink-3)]"> · {project.team}</span>
            )}
          </span>
          <StateChip card={project} />
        </>
      )}
    </li>
  );
}

function Group({ title, rows, away }: { title: string; rows: Connection[]; away: boolean }) {
  if (rows.length === 0) return null;
  return (
    <div className="flex min-w-[24rem] flex-1 flex-col gap-1">
      <h3 className="text-[11px] font-semibold text-[var(--pa-ink-3)]">{title}</h3>
      <ul className="flex flex-col gap-1">
        {rows.map((row) => (
          <Row
            key={`${row.item.data}:${row.item.id}:${row.project?.name ?? ""}`}
            connection={row}
            away={away}
          />
        ))}
      </ul>
    </div>
  );
}

export function ProjectConnections({ projectName }: { projectName: string }) {
  const { data } = useProjectConnections(projectName);
  if (!data || !hasConnections(data)) return null;
  const { project, livesIn, cameFrom, handedTo, reliesOn, reliedOnBy } = data;
  const linked = cameFrom.length + handedTo.length + reliesOn.length + reliedOnBy.length > 0;
  return (
    <section
      aria-label="Goal and connections"
      data-testid="project-connections"
      className="flex shrink-0 flex-col gap-2 px-4 pt-1 pb-3 font-[family-name:var(--pa-font)] text-[13px]"
    >
      {project && (project.goal || project.state) && (
        <div className="flex items-center gap-2">
          <p className="min-w-0 truncate text-[var(--pa-ink)]">
            <span className="font-semibold">Goal</span>
            {project.goal ? ` · ${project.goal}` : " · not written yet"}
          </p>
          <StateChip card={project} />
        </div>
      )}
      {(linked || livesIn) && (
        <div className="flex flex-col gap-2 rounded-[var(--pa-r-panel)] border border-[var(--pa-line)] bg-[var(--pa-surface)] p-3">
          <h2 className="font-semibold text-[var(--pa-ink)]">Connections</h2>
          <div className="flex flex-wrap gap-x-6 gap-y-3">
            {livesIn && (
              <div className="flex min-w-40 flex-col gap-1">
                <h3 className="text-[11px] font-semibold text-[var(--pa-ink-3)]">Lives in</h3>
                <p className="text-[var(--pa-ink)]">{livesIn}</p>
              </div>
            )}
            <Group title="Came from" rows={cameFrom} away={false} />
            <Group title="Handed to others" rows={handedTo} away />
            <Group title="Relies on" rows={reliesOn} away />
            <Group title="Others rely on this" rows={reliedOnBy} away={false} />
          </div>
        </div>
      )}
    </section>
  );
}
