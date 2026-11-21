// omnigent-slim: draws a ```participant block as that participant's own turn.
// Agents get a square mark, people a round one, and a person played by an
// agent keeps a dashed outline and a "stand-in" tag.

import type { ReactNode } from "react";
import { useInRouterContext } from "react-router-dom";
import { HANGAR_WRENCH_GROUP, HangarWrench } from "@/hangar/HangarWrench";
import { hangarPath, participantSlug, useAvatars } from "@/hangar/hangarApi";
import { withBasePath } from "@/lib/basePath";
import { type ParticipantTurn, participantInitials } from "@/lib/participantTurn";
import { Link } from "@/lib/routing";
import { cn } from "@/lib/utils";

export function ParticipantMark({
  name,
  kind,
  standIn,
  className,
}: {
  name: string;
  kind: "agent" | "person";
  standIn: boolean;
  className?: string;
}) {
  // omnigent-slim: a picture picked in the Hangar replaces the initials (D-74).
  const { data: avatars } = useAvatars();
  const picture = avatars?.[participantSlug(name)];
  return (
    <span
      aria-hidden="true"
      data-kind={kind}
      className={cn(
        "inline-grid size-6 shrink-0 place-items-center overflow-hidden border text-[10px] leading-none font-bold",
        kind === "person"
          ? "rounded-full bg-emerald-600/15 text-emerald-700 dark:text-emerald-300"
          : "rounded-md bg-sky-700/15 text-sky-800 dark:text-sky-300",
        standIn ? "border-dashed border-current" : "border-transparent",
        className,
      )}
    >
      {picture ? (
        <img src={picture} alt="" className="size-full rounded-[inherit] object-cover" />
      ) : (
        participantInitials(name)
      )}
    </span>
  );
}

function SessionLink({ id }: { id: string }) {
  const inRouter = useInRouterContext();
  const path = `/c/${encodeURIComponent(id)}`;
  const className =
    "ml-auto shrink-0 text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground";
  const title = "Open the background session that speaks for them";
  return inRouter ? (
    <Link to={path} className={className} title={title}>
      Open their session
    </Link>
  ) : (
    <a href={withBasePath(path)} className={className} title={title}>
      Open their session
    </a>
  );
}

export function ParticipantTurnBlock({
  turn,
  children,
  hangarLink = true,
}: {
  turn: ParticipantTurn;
  children: ReactNode;
  /** The hover-only wrench to this participant in the Hangar (off inside the Hangar). */
  hangarLink?: boolean;
}) {
  return (
    <section
      data-testid="participant-turn"
      data-participant={turn.name}
      aria-label={`${turn.name} says`}
      className={cn(
        "my-2 rounded-lg border border-l-[3px] border-border bg-muted/40",
        turn.kind === "person" ? "border-l-emerald-600" : "border-l-sky-700",
      )}
    >
      <header
        className={cn(
          "flex flex-wrap items-center gap-x-2 gap-y-1 px-3 pt-2 text-sm",
          HANGAR_WRENCH_GROUP,
        )}
      >
        <ParticipantMark name={turn.name} kind={turn.kind} standIn={turn.standIn} />
        <b className="font-semibold">{turn.name}</b>
        {turn.standIn ? (
          <span
            className="rounded border border-dashed border-amber-600 px-1 font-mono text-[10px] tracking-wide text-amber-700 uppercase dark:text-amber-400"
            title="An agent is playing this person"
          >
            stand-in
          </span>
        ) : (
          <span className="rounded border border-border px-1 font-mono text-[10px] tracking-wide text-muted-foreground uppercase">
            {turn.kind}
          </span>
        )}
        {turn.role && <span className="text-xs text-muted-foreground">{turn.role}</span>}
        {turn.sessionId && <SessionLink id={turn.sessionId} />}
        {hangarLink && (
          <HangarWrench
            to={hangarPath.person(participantSlug(turn.name))}
            label={`Open ${turn.name} in the Hangar`}
            className={turn.sessionId ? undefined : "ml-auto"}
          />
        )}
      </header>
      <div className="px-3 pt-1 pb-2">{children}</div>
    </section>
  );
}
