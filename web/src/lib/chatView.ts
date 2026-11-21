// omnigent-slim: a view the agent draws inside the chat.
//
// "Asks in chat, work in canvas" (docs/product/decisions.md): a question, a
// pick-one, a single card or a summary is drawn in the conversation, so the
// user can answer without losing what is open in the canvas. The agent renders
// the view to an HTML file as usual and names it in a fenced block:
//
//   ```view
//   file: artifacts/allowances-decision-D-1.html
//   title: Whose consent does an under-18 allowance need?
//   ```
//
// The chat shows that file in a sandboxed frame with the same `window.omnigent`
// bridge the canvas gives it. Once the user has replied, the view folds into a
// one-line record and stops accepting input.

/** The fence language that marks a view to draw in the chat. */
export const CHAT_VIEW_LANGUAGE = "view";

export interface ChatView {
  /** Workspace-relative path of the rendered view. */
  file: string;
  /** What the view is, for the folded record and the frame's label. */
  title: string | null;
}

// Only rendered views, inside the workspace: no absolute paths, no "..".
const VIEW_FILE = /^[A-Za-z0-9_][A-Za-z0-9_ ./-]{0,199}\.html$/;

/**
 * Read a ```view fence.
 *
 * @param text The fence's content.
 * @returns The view, or null when the fence names no usable file.
 */
export function parseChatView(text: string): ChatView | null {
  let file: string | null = null;
  let title: string | null = null;
  for (const line of text.split("\n")) {
    const match = /^\s*([a-z_]+)\s*:\s*(.*?)\s*$/.exec(line);
    if (!match) continue;
    if (match[1] === "file") file = match[2].replace(/^\.\//, "");
    if (match[1] === "title") title = match[2].slice(0, 200) || null;
  }
  if (!file || !VIEW_FILE.test(file) || file.split("/").includes("..")) return null;
  return { file, title };
}

/** Tag on the size messages a chat view posts (the view kit's own tag). */
const SIZE_SOURCE = "pa-kit";

/** The height a chat view reported for itself, or null for any other message. */
export function chatViewHeight(data: unknown): number | null {
  if (typeof data !== "object" || data === null) return null;
  const message = data as { source?: unknown; type?: unknown; height?: unknown };
  if (message.source !== SIZE_SOURCE || message.type !== "size") return null;
  return typeof message.height === "number" && Number.isFinite(message.height)
    ? message.height
    : null;
}

/**
 * Prepare a view's HTML for the chat: mark the host as "chat" before the view's
 * own script runs (the view kit then drops its page chrome), and report the
 * content height so the frame can fit it. Views not made with the kit get the
 * same size report.
 */
export function prepareChatView(html: string): string {
  const script = `<script data-omnigent-chat-view>(function () {
  document.documentElement.setAttribute("data-host", "chat");
  function report() {
    var body = document.body;
    if (!body) return;
    var height = Math.ceil(Math.max(body.scrollHeight, body.getBoundingClientRect().height));
    try { window.parent.postMessage({ source: ${JSON.stringify(SIZE_SOURCE)}, type: "size", height: height }, "*"); } catch (e) {}
  }
  window.addEventListener("load", function () {
    report();
    if (window.ResizeObserver && document.body) new ResizeObserver(report).observe(document.body);
  });
})();</script>`;
  const doctype = /^\s*<!doctype[^>]*>/i.exec(html);
  if (!doctype) return script + html;
  const end = doctype[0].length;
  return html.slice(0, end) + script + html.slice(end);
}

// ── Where the user's attention is needed ─────────────────────────────────────
// While a view in the chat is waiting for an answer, the canvas steps back
// (see `html[data-chat-asks]` in index.css) so it is plain where to look.

const waiting = new Set<string>();

function publish(): void {
  const root = document.documentElement;
  if (waiting.size > 0) root.setAttribute("data-chat-asks", String(waiting.size));
  else root.removeAttribute("data-chat-asks");
}

/**
 * Say that a chat view is waiting for the user.
 *
 * @returns Call to say it no longer is.
 */
export function markChatViewWaiting(id: string): () => void {
  waiting.add(id);
  publish();
  return () => {
    waiting.delete(id);
    publish();
  };
}
