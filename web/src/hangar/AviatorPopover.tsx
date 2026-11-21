/**
 * omnigent-slim: Aviator beside a draft, without leaving the Hangar (D-63).
 *
 * A pop-over at the bottom right holds a real session in the Hangar project,
 * working on the draft that is open. It can be pinned as a column. "Change"
 * is the chat itself; "Try them" sends a test question that the session asks
 * the unpublished draft, so the answer arrives as a real participant turn.
 * The session id is kept on the draft, so reopening the page finds the same
 * conversation.
 */

import { useQueryClient } from "@tanstack/react-query";
import { PinIcon, PinOffIcon, SparklesIcon, XIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { FullSessionChat } from "@/components/chat/FullSessionChat";
import { useResolveOrCreateProjectId } from "@/hooks/useConversations";
import { fetchAgentCatalog } from "@/hooks/useAvailableAgents";
import { fetchHosts } from "@/hooks/useHosts";
import { nativeAgentSortRank, nativeWrapperLabelsForAgent } from "@/lib/nativeCodingAgents";
import { createSession, sendUserMessage } from "@/lib/sessionsApi";
import { cn } from "@/lib/utils";
import {
  HANGAR_PROJECT,
  type HangarDraft,
  aviatorPrompt,
  trialPrompt,
  useHangarActions,
} from "./hangarApi";

/** Start a Claude session in the Hangar project, in the workspace, and send its first message. */
async function startAviatorSession(opts: {
  workspace: string;
  title: string;
  prompt: string;
  resolveProjectId: (name: string) => Promise<string>;
}): Promise<string> {
  const { agents } = await fetchAgentCatalog();
  const native = agents
    .filter((a) => nativeWrapperLabelsForAgent(a) !== undefined)
    .sort((a, b) => nativeAgentSortRank(a) - nativeAgentSortRank(b));
  const agent = native[0] ?? agents[0];
  if (!agent) throw new Error("No agent is available to start Aviator.");
  const host = (await fetchHosts(false)).find((h) => h.status === "online");
  if (!host) throw new Error("This computer is not connected, so Aviator can't start.");
  const projectId = await opts.resolveProjectId(HANGAR_PROJECT);
  const session = await createSession(agent.id, [], {
    projectId,
    hostId: host.host_id,
    workspace: opts.workspace,
    title: opts.title,
    labels: nativeWrapperLabelsForAgent(agent),
  });
  await sendUserMessage(session.id, opts.prompt);
  return session.id;
}

export function AviatorPopover({
  draft,
  name,
  workspace,
  pinned,
  onPinnedChange,
}: {
  draft: Pick<HangarDraft, "id" | "action" | "aviator">;
  name: string;
  workspace: string;
  pinned: boolean;
  onPinnedChange: (pinned: boolean) => void;
}) {
  const [open, setOpen] = useState(pinned);
  const [tab, setTab] = useState<"change" | "try">("change");
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resolveProjectId = useResolveOrCreateProjectId();
  const { edit } = useHangarActions();
  const client = useQueryClient();
  const sessionId = draft.aviator;

  // While Aviator is working, its edits to the draft file show on the page.
  useEffect(() => {
    if (!open || !sessionId) return;
    const timer = window.setInterval(
      () => void client.invalidateQueries({ queryKey: ["slim-hangar"] }),
      4000,
    );
    return () => window.clearInterval(timer);
  }, [open, sessionId, client]);

  async function start(first?: string) {
    setBusy(true);
    setError(null);
    try {
      const id = await startAviatorSession({
        workspace,
        title: `Hangar: ${name}`,
        prompt: first ?? aviatorPrompt(draft, name),
        resolveProjectId,
      });
      await edit.mutateAsync({ id: draft.id, edit: { aviator: id } });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function tryThem() {
    const q = question.trim();
    if (!q) return;
    setBusy(true);
    setError(null);
    try {
      if (sessionId) await sendUserMessage(sessionId, trialPrompt(draft.id, name, q));
      else await start(`${aviatorPrompt(draft, name)}\n\n${trialPrompt(draft.id, name, q)}`);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className="aviator-fab"
        onClick={() => setOpen(true)}
        data-testid="hangar-ask-aviator"
      >
        <SparklesIcon aria-hidden="true" className="size-4" /> Ask Aviator
      </button>
    );
  }
  const first = name.split(/\s+/)[0] || name;
  return (
    <div
      className={cn("aviator-pop", pinned && "pinned")}
      role="dialog"
      aria-label="Aviator"
      data-testid="hangar-aviator"
    >
      <header>
        <b>Aviator</b>
        <span className="dim">working on this draft</span>
        <span className="sp" />
        <button
          type="button"
          onClick={() => onPinnedChange(!pinned)}
          title={pinned ? "Unpin" : "Pin as a column"}
          aria-label={pinned ? "Unpin" : "Pin as a column"}
        >
          {pinned ? <PinOffIcon className="size-4" /> : <PinIcon className="size-4" />}
        </button>
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            onPinnedChange(false);
          }}
          aria-label="Close Aviator"
        >
          <XIcon className="size-4" />
        </button>
      </header>
      <div className="tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "change"}
          onClick={() => setTab("change")}
        >
          Change with Aviator
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "try"}
          onClick={() => setTab("try")}
          data-testid="hangar-try-tab"
        >
          Try them
        </button>
      </div>
      {tab === "try" && (
        <form
          className="try"
          onSubmit={(e) => {
            e.preventDefault();
            void tryThem();
          }}
        >
          <span className="dim">
            Ask {first} a real question. The draft answers the way people will meet them when
            flying. Nothing is published.
          </span>
          <div className="row">
            <input
              className="hangar-input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={`Ask ${first} a question…`}
              aria-label={`Question for ${name}`}
            />
            <button type="submit" className="hangar-btn pri" disabled={busy || !question.trim()}>
              Ask
            </button>
          </div>
        </form>
      )}
      <div className="body">
        {sessionId ? (
          <FullSessionChat key={sessionId} sessionId={sessionId} evenComposerPadding />
        ) : (
          <div className="start">
            <p>
              Aviator can rewrite the brief, suggest a call-for line, or change several things at
              once. Its changes land in this draft and show on the page as it works.
            </p>
            {tab === "change" && (
              <button
                type="button"
                className="hangar-btn pri"
                onClick={() => void start()}
                disabled={busy}
                data-testid="hangar-start-aviator"
              >
                {busy ? "Starting…" : "Start Aviator on this draft"}
              </button>
            )}
          </div>
        )}
        {error && <p className="chip fail">{error}</p>}
      </div>
    </div>
  );
}
