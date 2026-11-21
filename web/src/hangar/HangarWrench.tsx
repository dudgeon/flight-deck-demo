// omnigent-slim: the way from a thing met while flying to the same thing in the
// Hangar (D-41). It must never show in a screen recording of a demo, so it is a
// small wrench with no words, invisible until the pointer is over the thing it
// belongs to (the nearest `group/hangar` parent) or it has keyboard focus.

import { WrenchIcon } from "lucide-react";
import { useInRouterContext } from "react-router-dom";
import { withBasePath } from "@/lib/basePath";
import { Link } from "@/lib/routing";
import { cn } from "@/lib/utils";

/** Class for the element whose hover reveals the wrench. */
export const HANGAR_WRENCH_GROUP = "group/hangar";

export function HangarWrench({
  to,
  label,
  className,
}: {
  to: string;
  label: string;
  className?: string;
}) {
  const inRouter = useInRouterContext();
  const classes = cn(
    "inline-grid size-5 shrink-0 place-items-center rounded text-muted-foreground",
    "opacity-0 transition-opacity duration-150",
    "group-hover/hangar:opacity-40 hover:!opacity-100 focus-visible:opacity-100",
    "focus-visible:outline-2 focus-visible:outline-[var(--pa-build)]",
    className,
  );
  const icon = <WrenchIcon aria-hidden="true" className="size-3" strokeWidth={2} />;
  return inRouter ? (
    <Link to={to} className={classes} title={label} aria-label={label} data-testid="hangar-wrench">
      {icon}
    </Link>
  ) : (
    <a
      href={withBasePath(to)}
      className={classes}
      title={label}
      aria-label={label}
      data-testid="hangar-wrench"
    >
      {icon}
    </a>
  );
}
