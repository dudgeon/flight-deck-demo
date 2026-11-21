// omnigent-slim: the sidebar's count of a project's runs that need the person (D-96).

import { useProjectRuns } from "./projectRuns";

/** Sidebar: how many of a project's runs are waiting on the person. Nothing at zero. */
export function ProjectRunsBadge({ projectName }: { projectName: string }) {
  const { data } = useProjectRuns(projectName);
  const count = data?.needsYou ?? 0;
  if (count === 0) return null;
  return (
    <span
      data-testid="project-runs-badge"
      title={`${count} ${count === 1 ? "run needs" : "runs need"} you`}
      aria-label={`${count} ${count === 1 ? "run needs" : "runs need"} you`}
      className="ml-1 inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded-full bg-[var(--pa-attn-soft)] px-1 text-[10px] leading-none font-bold text-[var(--pa-attn)]"
    >
      {count}
    </span>
  );
}
