// omnigent-slim: lets an HTML artifact in the right-hand viewer talk back to
// the session. The preview iframe gets a tiny `window.omnigent` API; calling
// `omnigent.prompt("text")` puts that text in the session's composer, where the
// user reviews it and presses Enter. Nothing is sent without the user.
//
// The iframe is sandboxed with an opaque origin, so postMessage is the only way
// out; the host accepts messages only from the frame it rendered.

/** Tag on every message an artifact posts to the host. */
export const ARTIFACT_BRIDGE_SOURCE = "omnigent-slim-artifact";

/** Window event the composer listens for. `detail` is {@link ArtifactPromptDetail}. */
export const ARTIFACT_PROMPT_EVENT = "omnigent-slim:artifact-prompt";

export interface ArtifactPromptDetail {
  text: string;
}

/** Longest text an artifact may hand to the composer. */
const MAX_PROMPT_CHARS = 20_000;

const RUNTIME = `<script data-omnigent-artifact-bridge>(function () {
  if (window.omnigent) return;
  function post(type, text) {
    window.parent.postMessage(
      { source: ${JSON.stringify(ARTIFACT_BRIDGE_SOURCE)}, type: type, text: String(text == null ? "" : text) },
      "*"
    );
  }
  window.omnigent = {
    /** Put text in the session composer for the user to review and send. */
    prompt: function (text) { post("prompt", text); }
  };
})();</script>`;

/** Insert the `window.omnigent` runtime at the top of an artifact's HTML. */
export function injectArtifactBridge(html: string): string {
  const doctype = /^\s*<!doctype[^>]*>/i.exec(html);
  if (!doctype) return RUNTIME + html;
  const end = doctype[0].length;
  return html.slice(0, end) + RUNTIME + html.slice(end);
}

/**
 * Turn a message from the artifact frame into a composer event.
 *
 * @param data `MessageEvent.data` from the frame.
 * @returns Whether the message was an artifact prompt and was dispatched.
 */
export function handleArtifactMessage(data: unknown): boolean {
  if (typeof data !== "object" || data === null) return false;
  const message = data as { source?: unknown; type?: unknown; text?: unknown };
  if (message.source !== ARTIFACT_BRIDGE_SOURCE || message.type !== "prompt") return false;
  if (typeof message.text !== "string" || !message.text.trim()) return false;
  const detail: ArtifactPromptDetail = { text: message.text.slice(0, MAX_PROMPT_CHARS) };
  window.dispatchEvent(new CustomEvent(ARTIFACT_PROMPT_EVENT, { detail }));
  return true;
}
