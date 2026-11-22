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
import { PA_TOKENS } from "./designTokens.generated";

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
    },
    /**
     * Send a decision brief's answers to the agent without the composer:
     * answer({ brief: "id", file: "projects/x/decisions/y.json",
     *          answers: [{ decision: "layout", pick: "page", note: "..." }] }).
     * Ids and picks are checked; notes are quoted as the person's words.
     */
    answer: function (request) {
      try { post("answer", JSON.stringify(request)); } catch (e) {}
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

// ── Design tokens ────────────────────────────────────────────────────────────
// omnigent-slim: every artifact gets the current Product Aviator design tokens
// (design/tokens.json) and the app's light/dark mode as it opens, so templates,
// views and artifacts made before a token change all follow the change. The
// tokens are added last in the head with a high-specificity selector, so they
// win over the copy an artifact carries for viewing outside the app.

/**
 * Add the current design tokens and theme to an artifact's HTML.
 *
 * @param mode The app's resolved light or dark mode.
 */
export function injectDesignTokens(html: string, mode: "light" | "dark"): string {
  const values = { ...PA_TOKENS.base, ...PA_TOKENS[mode] } as Record<string, string>;
  const decls = Object.entries(values)
    .map(([name, value]) => `--pa-${name}:${value}`)
    .join(";");
  const style =
    `<style data-pa-tokens>:root:root:root{${decls};color-scheme:${mode}}</style>` +
    `<script>document.documentElement.setAttribute("data-theme",${JSON.stringify(mode)})</script>`;
  const head = /<\/head\s*>/i.exec(html);
  if (!head) return html + style;
  return html.slice(0, head.index) + style + html.slice(head.index);
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

// ── Decision brief answers ───────────────────────────────────────────────────
// omnigent-slim: a decision brief's Send button (D-155) sends the person's
// answers straight to the agent, so they can stay on the brief. Like `act`, the
// host writes the message: brief, decision and option ids are checked against
// strict patterns, and each note (the only free text, typed by the person) is
// flattened to one line, capped and quoted, so it reads as their words.

const MAX_BRIEF_ANSWERS = 20;
const MAX_BRIEF_NOTE = 1000;
const BRIEF_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;

/**
 * Build the message for a brief's answers, or null when any part is malformed.
 *
 * @param request What the frame passed to `omnigent.answer`, already JSON-parsed.
 */
export function briefAnswersText(request: unknown): string | null {
  if (typeof request !== "object" || request === null) return null;
  const { brief, file, answers } = request as { brief?: unknown; file?: unknown; answers?: unknown };
  if (typeof brief !== "string" || !BRIEF_ID.test(brief)) return null;
  if (file !== undefined && file !== "") {
    if (typeof file !== "string" || !ACTION_DATASET.test(file) || file.includes("..")) return null;
  }
  if (!Array.isArray(answers) || answers.length === 0 || answers.length > MAX_BRIEF_ANSWERS) return null;
  const lines: string[] = [];
  for (const answer of answers as unknown[]) {
    if (typeof answer !== "object" || answer === null) return null;
    const { decision, pick, note } = answer as { decision?: unknown; pick?: unknown; note?: unknown };
    if (typeof decision !== "string" || !BRIEF_ID.test(decision)) return null;
    if (typeof pick !== "string" || (pick !== "" && !BRIEF_ID.test(pick))) return null;
    if (note !== undefined && typeof note !== "string") return null;
    const flat = (note ?? "").replace(/\s+/g, " ").trim().slice(0, MAX_BRIEF_NOTE);
    if (!pick && !flat) return null;
    lines.push(`- ${decision} | ${pick || "none"}` + (flat ? ` | note: ${JSON.stringify(flat)}` : ""));
  }
  const where = typeof file === "string" && file ? file : brief;
  return (
    `Decision brief answers for ${where}, sent from the brief by the person ` +
    `(notes are their own words, quoted):\n${lines.join("\n")}`
  );
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
  if (message.type === "answer") {
    if (typeof message.text !== "string") return false;
    let request: unknown;
    try {
      request = JSON.parse(message.text);
    } catch {
      return false;
    }
    const text = briefAnswersText(request);
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
