// omnigent-slim: the direct line in a director's chat (D-116): the thread's
// turns inside a rail (D-91), and the strip on the message box (D-90).
//
// Intent: the person stays with the director and still does the work. The
// rail says which work a turn belongs to; who is speaking stays as it is
// inside it. The strip is always in view and says who the message box is
// talking to, because a message must have one obvious destination (D-94).

import { PauseIcon } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useRef } from "react";
import { computeIsWorking, withUncommittedUserBubbles } from "@/components/chat/chatBubbleParts";
import { ConversationScopeContext } from "@/components/chat/conversationScope";
import { useConversationEntryState } from "@/hooks/useConversationEntryState";
import {
  PAUSE_MESSAGE,
  registerDirectLine,
  setLineTarget,
  useDirectLineRun,
  useLineTarget,
} from "@/lib/directLine";
import { getCurrentAuthorId } from "@/lib/identity";
import { type Bubble, type BubbleCache, buildBubbles, createBubbleCache } from "@/lib/renderItems";
import { Link } from "@/lib/routing";
import { cn } from "@/lib/utils";
import { CHAT_COLUMN_WIDTH } from "@/pages/chatLayout";
import { type ProjectRun, runStepLine } from "@/projectHome/projectRuns";
import { RunStateChip } from "@/projectHome/RunParts";
import { ensureConversationStreamed, useChatStore } from "@/store/chatStore";

const NO_BUBBLES: Bubble[] = [];

/** "Intent shaping · Teen allowances". */
function runName(run: ProjectRun): string {
  return run.subject ? `${run.workflow} · ${run.subject}` : run.workflow;
}

export interface DirectLineBubbles {
  run: ProjectRun | null;
  threadId: string | null;
  /** The thread's turns, oldest first; empty when no thread has the floor. */
  bubbles: Bubble[];
}

/** The thread with the floor in this director's chat, and its turns as they stream. */
export function useDirectLineBubbles(directorId: string | null): DirectLineBubbles {
  const run = useDirectLineRun(directorId);
  const threadId = run?.session ?? null;
  useEffect(() => {
    if (threadId) void ensureConversationStreamed(threadId);
  }, [threadId]);
  const state = useConversationEntryState(threadId);
  const agentId = state.boundAgentId;
  useEffect(() => {
    if (!directorId) return;
    registerDirectLine(directorId, threadId ? { threadId, agentId } : null);
  }, [directorId, threadId, agentId]);
  useEffect(() => {
    if (!directorId) return;
    return () => registerDirectLine(directorId, null);
  }, [directorId]);
  const cacheRef = useRef<{ threadId: string | null; cache: BubbleCache }>({
    threadId: null,
    cache: createBubbleCache(),
  });
  if (cacheRef.current.threadId !== threadId) {
    cacheRef.current = { threadId, cache: createBubbleCache() };
  }
  const {
    blocks,
    activeResponse,
    interruptedResponseIds,
    sessionStatus,
    pendingUserMessages,
    failedInputs,
  } = state;
  const bubbles = useMemo(() => {
    if (!threadId) return NO_BUBBLES;
    return withUncommittedUserBubbles(
      buildBubbles(
        blocks,
        activeResponse,
        cacheRef.current.cache,
        interruptedResponseIds,
        computeIsWorking(sessionStatus),
      ),
      pendingUserMessages,
      failedInputs,
      getCurrentAuthorId(),
    );
  }, [
    threadId,
    blocks,
    activeResponse,
    interruptedResponseIds,
    sessionStatus,
    pendingUserMessages,
    failedInputs,
  ]);
  return { run, threadId, bubbles };
}

export interface LineRail {
  threadId: string;
  label: string;
  /** Row keys of the bubbles that belong to the thread. */
  keys: ReadonlySet<string>;
}

export function lineRailFor(
  line: DirectLineBubbles,
  bubbles: readonly Bubble[],
  keyOf: (bubble: Bubble) => string,
): LineRail | null {
  if (!line.threadId || !line.run || bubbles.length === 0) return null;
  return { threadId: line.threadId, label: runName(line.run), keys: new Set(bubbles.map(keyOf)) };
}

/**
 * One transcript row. A row that belongs to the thread gets the rail, and its
 * actions (answering a question, retrying) reach the thread, not the director.
 */
export function DirectLineRow({
  rail,
  rowKey,
  startsGroup,
  children,
}: {
  rail: LineRail | null | undefined;
  rowKey: string;
  /** The row before this one is not the thread's: name the work here. */
  startsGroup: boolean;
  children: ReactNode;
}) {
  if (!rail || !rail.keys.has(rowKey)) return children;
  return (
    <ConversationScopeContext.Provider value={rail.threadId}>
      <div data-testid="line-rail" className="border-l-2 border-[var(--pa-agent)] pl-3">
        {startsGroup && (
          <p className="pb-1 text-[11px] font-semibold text-[var(--pa-agent)]">{rail.label}</p>
        )}
        {children}
      </div>
    </ConversationScopeContext.Provider>
  );
}

const FOCUS =
  "outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--pa-navy)]";
const QUIET_BUTTON = cn(
  "flex shrink-0 items-center gap-1 rounded-[var(--pa-r)] border border-[var(--pa-line-strong)] px-2 py-0.5 text-[12px] font-medium text-[var(--pa-ink)] hover:bg-[var(--pa-sunk)]",
  FOCUS,
);

/** The one-line strip on the message box: who it is talking to, the step, Pause. */
export function DirectLineStrip({ directorId }: { directorId: string | null }) {
  const run = useDirectLineRun(directorId);
  const target = useLineTarget(directorId);
  const threadAgentId = useConversationEntryState(run?.session ?? null).boundAgentId;
  const directorAgentId = useChatStore((s) => s.boundAgentId);
  if (!directorId || !run || !run.session) return null;
  const threadId = run.session;
  const toThread = target === "thread";
  const pause = () => {
    const agentId = threadAgentId ?? directorAgentId;
    if (!agentId) return;
    void useChatStore
      .getState()
      .send(PAUSE_MESSAGE, agentId, undefined, { pinnedConversationId: threadId });
  };
  return (
    <div
      data-testid="line-strip"
      data-target={target}
      className={cn(
        "mx-auto mb-1.5 flex w-full items-center gap-2 rounded-[var(--pa-r)] border px-3 py-1.5 text-[12px]",
        CHAT_COLUMN_WIDTH,
        toThread
          ? "border-[var(--pa-agent)] bg-[var(--pa-agent-soft)]"
          : "border-[var(--pa-line)] bg-[var(--pa-sunk)]",
      )}
    >
      <span className="min-w-0 flex-1 truncate text-[var(--pa-ink-2)]">
        {toThread ? (
          <>
            Talking to{" "}
            <Link
              to={`/c/${threadId}`}
              title="Step into the thread"
              className={cn("font-semibold text-[var(--pa-ink)] no-underline hover:underline", FOCUS)}
            >
              {runName(run)}
            </Link>{" "}
            · {runStepLine(run)}
          </>
        ) : (
          <>
            Talking to <span className="font-semibold text-[var(--pa-ink)]">Aviator</span> ·{" "}
            {runName(run)} carries on
          </>
        )}
      </span>
      <RunStateChip state={run.state} />
      {toThread ? (
        <>
          <button type="button" className={QUIET_BUTTON} onClick={pause}>
            <PauseIcon aria-hidden="true" className="size-3" />
            Pause
          </button>
          <button
            type="button"
            className={QUIET_BUTTON}
            onClick={() => setLineTarget(directorId, "aviator")}
          >
            Talk to Aviator
          </button>
        </>
      ) : (
        <button
          type="button"
          className={QUIET_BUTTON}
          onClick={() => setLineTarget(directorId, "thread")}
        >
          Back to the thread
        </button>
      )}
    </div>
  );
}
