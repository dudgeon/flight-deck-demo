// omnigent-slim: lets an HTML artifact in the right-hand viewer talk back to
// the session. The preview iframe gets a tiny `window.omnigent` API; calling
// `omnigent.prompt("text")` puts that text in the session's composer, where the
// user reviews it and presses Enter. Nothing is sent without the user.
//
// The iframe is sandboxed with an opaque origin, so postMessage is the only way
// out; the host accepts messages only from the frame it rendered.
//
// The same runtime answers the canvas tools (canvas_read, canvas_click, ...):
// see canvasFrameRuntime.ts and canvasRelay.ts.

import { CANVAS_FRAME_RUNTIME } from "./canvasFrameRuntime";

/** Tag on every message an artifact posts to the host. */
export const ARTIFACT_BRIDGE_SOURCE = "omnigent-slim-artifact";

/** Window event the composer listens for. `detail` is {@link ArtifactPromptDetail}. */
export const ARTIFACT_PROMPT_EVENT = "omnigent-slim:artifact-prompt";

export interface ArtifactPromptDetail {
  text: string;
}

/**
 * Window event for a state change an artifact sends straight to the agent.
 * `detail` is {@link ArtifactActionDetail}; the chat page sends `detail.text`.
 */
export const ARTIFACT_ACTION_EVENT = "omnigent-slim:artifact-action";

export interface ArtifactActionDetail {
  /** The message to send, written by the host from validated values. */
  text: string;
}

/** Longest text an artifact may hand to the composer. */
const MAX_PROMPT_CHARS = 20_000;

// ── View state ───────────────────────────────────────────────────────────────
// The viewer reloads an artifact whenever its file changes, and the frame has no
// storage of its own (opaque origin). `omnigent.saveState(key, value)` hands the
// host a small JSON value, and the next load of the same file gets it back as
// `omnigent.state[key]`. So a view keeps its open card, filters and unsent edits
// while the agent rewrites the data under it.

/** Largest state one artifact may keep, as JSON text. */
const MAX_STATE_CHARS = 200_000;
const STATE_STORAGE_PREFIX = "omnigent-slim:artifact-state:";

/** Saved state for one artifact: `{ [key]: value }`. */
export type ArtifactState = Record<string, unknown>;

const artifactStates = new Map<string, ArtifactState>();

/** Identifies one artifact's state: the session and the file's workspace path. */
export function artifactStateScope(conversationId: string, path: string | null): string | null {
  return path ? `${conversationId}:${path}` : null;
}

/** The state saved for an artifact, or an empty object. */
export function readArtifactState(scope: string | null): ArtifactState {
  if (!scope) return {};
  const cached = artifactStates.get(scope);
  if (cached) return cached;
  let state: ArtifactState = {};
  try {
    const raw = window.localStorage.getItem(STATE_STORAGE_PREFIX + scope);
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
      state = parsed as ArtifactState;
    }
  } catch {
    // Unreadable storage only costs the saved state.
  }
  artifactStates.set(scope, state);
  return state;
}

function writeArtifactState(scope: string, key: string, json: string): void {
  let value: unknown;
  try {
    value = JSON.parse(json);
  } catch {
    return;
  }
  const next = { ...readArtifactState(scope), [key]: value };
  const text = JSON.stringify(next);
  if (text.length > MAX_STATE_CHARS) return;
  artifactStates.set(scope, next);
  try {
    window.localStorage.setItem(STATE_STORAGE_PREFIX + scope, text);
  } catch {
    // Kept in memory for this page load.
  }
}

function runtime(state: ArtifactState): string {
  // "<" is escaped so saved text can never close the script element.
  const stateJson = JSON.stringify(state).replace(/</g, "\\u003c");
  return `<script data-omnigent-artifact-bridge>(function () {
  if (window.omnigent) return;
  var SOURCE = ${JSON.stringify(ARTIFACT_BRIDGE_SOURCE)};
  function post(type, text, key) {
    window.parent.postMessage(
      { source: SOURCE, type: type, text: String(text == null ? "" : text), key: key },
      "*"
    );
  }
  window.omnigent = {
    /** Put text in the session composer for the user to review and send. */
    prompt: function (text) { post("prompt", text); },
    /** What this artifact saved before it was last reloaded: { key: value }. */
    state: ${stateJson},
    /** Keep a small JSON value across reloads of this artifact. */
    saveState: function (key, value) {
      try { post("state", JSON.stringify(value === undefined ? null : value), String(key)); } catch (e) {}
    },
    /**
     * Send state changes to the agent without the composer:
     * act({ dataset: "data/x.json", changes: [{ id: "R-01", field: "status", value: "reviewed" }] }).
     * Only state fields and plain status words are accepted; the host writes the message.
     */
    act: function (request) {
      try { post("act", JSON.stringify(request)); } catch (e) {}
    }
  };
${CANVAS_FRAME_RUNTIME}
})();</script>`;
}

/**
 * Insert the `window.omnigent` runtime at the top of an artifact's HTML.
 *
 * @param state What the artifact saved earlier, given back as `omnigent.state`.
 */
export function injectArtifactBridge(html: string, state: ArtifactState = {}): string {
  const script = runtime(state);
  const doctype = /^\s*<!doctype[^>]*>/i.exec(html);
  if (!doctype) return script + html;
  const end = doctype[0].length;
  return html.slice(0, end) + script + html.slice(end);
}

// ── Direct actions ───────────────────────────────────────────────────────────
// `omnigent.act(...)` is the one way an artifact reaches the agent without the
// user pressing Send, so it is deliberately narrow. The frame supplies only
// record ids, state field names and status words, each checked against a strict
// pattern; the host composes the sentence. An artifact therefore cannot use the
// channel to give the agent instructions, only to report a state change the
// user made in the view. Anything else goes through `omnigent.prompt`.

const MAX_ACTION_CHANGES = 50;
const MIN_ACTION_INTERVAL_MS = 400;
const ACTION_DATASET = /^[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}$/;
const ACTION_ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$/;
const ACTION_FIELD = /^(status|locked|[a-z][a-z0-9_]{0,30}_status)$/;
const ACTION_VALUE = /^[a-z][a-z0-9-]{0,30}$/;

let lastActionAt = 0;

/**
 * Build the message for a direct action, or null when any part is not a plain
 * state change.
 *
 * @param request What the frame passed to `omnigent.act`, already JSON-parsed.
 */
export function artifactActionText(request: unknown): string | null {
  if (typeof request !== "object" || request === null) return null;
  const { dataset, changes } = request as { dataset?: unknown; changes?: unknown };
  if (typeof dataset !== "string" || !ACTION_DATASET.test(dataset) || dataset.includes("..")) {
    return null;
  }
  if (!Array.isArray(changes) || changes.length === 0 || changes.length > MAX_ACTION_CHANGES) {
    return null;
  }
  const lines: string[] = [];
  for (const change of changes as unknown[]) {
    if (typeof change !== "object" || change === null) return null;
    const { id, field, value } = change as { id?: unknown; field?: unknown; value?: unknown };
    if (typeof id !== "string" || !ACTION_ID.test(id)) return null;
    if (typeof field !== "string" || !ACTION_FIELD.test(field)) return null;
    const valid =
      typeof value === "boolean" || (typeof value === "string" && ACTION_VALUE.test(value));
    if (!valid) return null;
    lines.push(`- ${id} ${field} = ${String(value)}`);
  }
  return `Canvas action on ${dataset}:\n${lines.join("\n")}`;
}

/**
 * Turn a message from the artifact frame into a composer event.
 *
 * @param data `MessageEvent.data` from the frame.
 * @param stateScope Where this artifact's saved state goes; null keeps none.
 * @returns Whether the message was an artifact prompt or state save and was handled.
 */
export function handleArtifactMessage(data: unknown, stateScope: string | null = null): boolean {
  if (typeof data !== "object" || data === null) return false;
  const message = data as { source?: unknown; type?: unknown; text?: unknown; key?: unknown };
  if (message.source !== ARTIFACT_BRIDGE_SOURCE) return false;
  if (message.type === "state") {
    if (!stateScope || typeof message.key !== "string" || typeof message.text !== "string") {
      return false;
    }
    writeArtifactState(stateScope, message.key.slice(0, 200), message.text);
    return true;
  }
  if (message.type === "act") {
    if (typeof message.text !== "string") return false;
    let request: unknown;
    try {
      request = JSON.parse(message.text);
    } catch {
      return false;
    }
    const text = artifactActionText(request);
    const now = Date.now();
    if (!text || now - lastActionAt < MIN_ACTION_INTERVAL_MS) return false;
    lastActionAt = now;
    const action: ArtifactActionDetail = { text };
    window.dispatchEvent(new CustomEvent(ARTIFACT_ACTION_EVENT, { detail: action }));
    return true;
  }
  if (message.type !== "prompt") return false;
  if (typeof message.text !== "string" || !message.text.trim()) return false;
  const detail: ArtifactPromptDetail = { text: message.text.slice(0, MAX_PROMPT_CHARS) };
  window.dispatchEvent(new CustomEvent(ARTIFACT_PROMPT_EVENT, { detail }));
  return true;
}
