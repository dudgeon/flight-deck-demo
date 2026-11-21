// omnigent-slim: draws a ```view fence as a live view inside the chat.
// See lib/chatView.ts for the contract.

import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import {
  artifactStateScope,
  handleArtifactMessage,
  injectArtifactBridge,
  injectDesignTokens,
  readArtifactState,
} from "@/lib/artifactBridge";
import {
  type ChatView,
  chatViewHeight,
  markChatViewWaiting,
  prepareChatView,
} from "@/lib/chatView";
import { cn } from "@/lib/utils";
import { fileContentText, workspaceSidebarSource } from "@/lib/workspaceSidebarSource";
import { useResolvedThemeMode } from "@/components/theme/useResolvedThemeMode";
import { useFileViewer } from "@/shell/FileViewerContext";
import { HTML_PREVIEW_SANDBOX } from "@/shell/codeViewerHelpers";
import { useChatStore } from "@/store/chatStore";

const MIN_HEIGHT = 72;
const MAX_HEIGHT = 720;
const REFRESH_MS = 4000;

/** Whether the user has written anything after the message that holds this view. */
function useAnswered(file: string): boolean {
  return useChatStore((s) => {
    const marker = `file: ${file}`;
    let at = -1;
    s.blocks.forEach((block, index) => {
      if (block.type === "text_done" && block.fullText.includes(marker)) at = index;
      if (block.type === "text_chunk" && block.text.includes(marker)) at = index;
    });
    if (at === -1) return false;
    return s.blocks.slice(at + 1).some((block) => block.type === "user_message");
  });
}

function name(view: ChatView): string {
  if (view.title) return view.title;
  const base = view.file.split("/").pop() ?? view.file;
  return base.replace(/\.html$/, "").replace(/[-_]+/g, " ");
}

/** A view drawn in the conversation: live until the user replies, then a record. */
export function ChatViewBlock({ view }: { view: ChatView }) {
  const conversationId = useChatStore((s) => s.conversationId);
  const idle = useChatStore((s) => s.status === "idle");
  const answered = useAnswered(view.file);
  const openFile = useFileViewer();
  const themeMode = useResolvedThemeMode() === "dark" ? "dark" : "light";
  const [shown, setShown] = useState(false);
  const [height, setHeight] = useState(MIN_HEIGHT);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const id = useId();
  const live = !answered;
  const visible = live || shown;

  const { data: content, isError } = useQuery({
    queryKey: ["slim-chat-view", conversationId, view.file],
    queryFn: async ({ signal }) => {
      const read = await workspaceSidebarSource().readFile(conversationId ?? "", view.file, signal);
      return fileContentText(read);
    },
    enabled: Boolean(conversationId) && visible,
    // The agent redraws the file as the data under it changes.
    refetchInterval: live ? REFRESH_MS : false,
    retry: 2,
  });

  const stateScope = artifactStateScope(conversationId ?? "", `chat:${view.file}`);
  const srcDoc = useMemo(() => {
    if (!content) return null;
    return injectDesignTokens(
      injectArtifactBridge(prepareChatView(content), readArtifactState(stateScope)),
      themeMode,
    );
  }, [content, stateScope, themeMode]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const frame = frameRef.current?.contentWindow;
      if (!frame || event.source !== frame) return;
      const size = chatViewHeight(event.data);
      if (size !== null) {
        setHeight(Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, size + 4)));
        return;
      }
      // A folded record is read-only: it keeps its place but sends nothing.
      if (live) handleArtifactMessage(event.data, stateScope);
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [live, stateScope]);

  // The canvas steps back while this view is the thing to answer.
  const asking = live && idle && Boolean(srcDoc);
  useEffect(() => (asking ? markChatViewWaiting(id) : undefined), [asking, id]);

  return (
    <div
      data-testid="chat-view"
      data-state={live ? "live" : "answered"}
      className={cn(
        "not-prose my-2 overflow-hidden rounded-lg border bg-card",
        asking ? "border-primary/60 shadow-sm" : "border-border",
      )}
    >
      <div className="flex items-center gap-2 border-b border-border/60 px-3 py-1.5 text-xs text-muted-foreground">
        <span className="min-w-0 flex-1 truncate font-medium text-foreground">{name(view)}</span>
        {!live && <span data-testid="chat-view-answered">Answered</span>}
        {!live && (
          <button
            type="button"
            className="rounded px-1.5 py-0.5 hover:bg-muted hover:text-foreground"
            onClick={() => setShown((value) => !value)}
          >
            {shown ? "Hide" : "Show"}
          </button>
        )}
        {openFile && (
          <button
            type="button"
            className="rounded px-1.5 py-0.5 hover:bg-muted hover:text-foreground"
            onClick={() => openFile(view.file)}
          >
            Open in canvas
          </button>
        )}
      </div>
      {visible &&
        (srcDoc ? (
          <iframe
            ref={frameRef}
            title={name(view)}
            srcDoc={srcDoc}
            sandbox={HTML_PREVIEW_SANDBOX}
            style={{ height }}
            className={cn("block w-full border-0", !live && "pointer-events-none opacity-80")}
          />
        ) : (
          <div className="px-3 py-3 text-xs text-muted-foreground">
            {isError || content === null
              ? `Could not read ${view.file}. Use "Open in canvas" to try there.`
              : "Drawing the view…"}
          </div>
        ))}
    </div>
  );
}
