// omnigent-slim: what a thread's page knows about its director (D-117).
//
// Stepping into a thread puts the thread in place of the chat. The director
// (the Aviator session that started it) folds to a bar on top: the way back,
// this thread's run, and what else is in flight in the project. The server
// answers all of that at `GET /v1/slim/threads/<session>`.

import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/identity";
import { parseProjectRun, type ProjectRun } from "@/projectHome/projectRuns";

export interface ThreadContext {
  director: { id: string; title: string };
  /** The run this thread is working, once it has written its first step. */
  run: ProjectRun | null;
  /** The project's other runs still in flight, the ones needing the person first. */
  others: ProjectRun[];
  needsYou: number;
}

/** Read the `GET /v1/slim/threads/<session>` answer; null when the session is not a thread. */
export function parseThreadContext(raw: unknown): ThreadContext | null {
  const thread =
    typeof raw === "object" && raw !== null ? (raw as { thread?: unknown }).thread : null;
  if (typeof thread !== "object" || thread === null) return null;
  const data = thread as Record<string, unknown>;
  const director = data.director as { id?: unknown; title?: unknown } | null | undefined;
  if (!director || typeof director.id !== "string" || !director.id) return null;
  const others = (Array.isArray(data.others) ? data.others : [])
    .map(parseProjectRun)
    .filter((run): run is ProjectRun => run !== null);
  return {
    director: {
      id: director.id,
      title: typeof director.title === "string" ? director.title.trim() : "",
    },
    run: parseProjectRun(data.run),
    others,
    needsYou: others.filter((run) => run.state === "needs-you").length,
  };
}

/** "2 others in flight", "1 other in flight", or "" when this is the only one. */
export function othersLabel(count: number): string {
  if (count <= 0) return "";
  return `${count} ${count === 1 ? "other" : "others"} in flight`;
}

const REFRESH_MS = 5000;

/** The thread context for a session, re-read while its page is open. */
export function useThreadContext(conversationId: string | null): ThreadContext | null {
  const { data } = useQuery({
    queryKey: ["slim-thread-context", conversationId],
    queryFn: async ({ signal }) => {
      const res = await authenticatedFetch(
        `/v1/slim/threads/${encodeURIComponent(conversationId ?? "")}`,
        { signal },
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return parseThreadContext(await res.json());
    },
    enabled: Boolean(conversationId),
    refetchInterval: (query) => (query.state.data ? REFRESH_MS : false),
    placeholderData: (previous, previousQuery) =>
      previousQuery?.queryKey[1] === conversationId ? previous : undefined,
    retry: false,
  });
  return data ?? null;
}
