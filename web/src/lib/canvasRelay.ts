// omnigent-slim: the host half of the canvas tools.
//
// The agent's canvas_* tools reach the server's claim-first action relay
// (`browser.action_request` on the session stream, the same route the desktop
// app's browser tools use) with action names that start with `canvas_`. This
// module listens for those, claims an action only when this tab is showing an
// HTML artifact for that session, forwards it into the viewer frame by
// postMessage (canvasFrameRuntime.ts runs it there) and posts the result back.
// Tabs that aren't showing the session's canvas don't claim, so the action goes
// to the tab the user is looking at, or fails fast with "nothing is open".

import { onBrowserActionRequest } from "./browserActionBus";
import { CANVAS_REQUEST_SOURCE } from "./canvasFrameRuntime";
import type { BrowserActionRequestEvent } from "./events";
import { authenticatedFetch } from "./identity";
import { ARTIFACT_BRIDGE_SOURCE } from "./artifactBridge";
import { randomUUID } from "./randomUUID";

/** Whether an action request is for the canvas tools. */
export function isCanvasAction(action: string): boolean {
  return action.startsWith("canvas_");
}

interface CanvasFrame {
  getWindow: () => Window | null | undefined;
  path: string | null;
}

/** The viewer frame showing each session's HTML artifact, most recent last. */
const frames = new Map<string, CanvasFrame[]>();
const pending = new Map<string, (result: Record<string, unknown>) => void>();
/** Stops re-sending a request once the frame has it. */
const acks = new Map<string, () => void>();
/** Each session's actions run one at a time, in the order the agent sent them. */
const queues = new Map<string, Promise<void>>();

/** Frame answers arrive well inside the server's 30s wait. */
const FRAME_TIMEOUT_MS = 25_000;
/** Re-post until the frame answers, in case it was still loading. */
const RESEND_MS = 400;

/**
 * Register a viewer frame as a session's canvas; returns an unregister.
 *
 * @param conversationId The session whose artifact the frame shows.
 * @param getWindow Returns the frame's current `contentWindow`.
 * @param path Workspace path of the file shown, when known.
 */
export function registerCanvasFrame(
  conversationId: string,
  getWindow: () => Window | null | undefined,
  path: string | null,
): () => void {
  ensureCanvasRelay();
  const entry: CanvasFrame = { getWindow, path };
  const list = frames.get(conversationId) ?? [];
  list.push(entry);
  frames.set(conversationId, list);
  return () => {
    const current = frames.get(conversationId);
    if (!current) return;
    const next = current.filter((e) => e !== entry);
    if (next.length) frames.set(conversationId, next);
    else frames.delete(conversationId);
  };
}

function currentFrame(conversationId: string): CanvasFrame | null {
  const list = frames.get(conversationId);
  if (!list) return null;
  for (let i = list.length - 1; i >= 0; i--) {
    if (list[i].getWindow()) return list[i];
  }
  return null;
}

/**
 * Handle a message from an artifact frame if it is a canvas result.
 *
 * @param data `MessageEvent.data`, already checked to come from a viewer frame.
 * @returns Whether it was a canvas result.
 */
export function handleCanvasResult(data: unknown): boolean {
  if (typeof data !== "object" || data === null) return false;
  const m = data as { source?: unknown; type?: unknown; id?: unknown; result?: unknown };
  if (m.source !== ARTIFACT_BRIDGE_SOURCE) return false;
  if (m.type === "canvas-ack") {
    if (typeof m.id === "string") acks.get(m.id)?.();
    return true;
  }
  if (m.type !== "canvas-result") return false;
  if (typeof m.id !== "string") return true;
  const resolve = pending.get(m.id);
  if (resolve) {
    pending.delete(m.id);
    resolve(
      typeof m.result === "object" && m.result !== null
        ? (m.result as Record<string, unknown>)
        : { ok: false, error: "the canvas sent back an unreadable result" },
    );
  }
  return true;
}

function runInFrame(
  conversationId: string,
  action: string,
  args: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const id = randomUUID();
  return new Promise((resolve) => {
    let resendTimer: ReturnType<typeof setInterval> | null = null;
    let received = false;
    const stopResending = () => {
      received = true;
      if (resendTimer !== null) clearInterval(resendTimer);
      resendTimer = null;
      acks.delete(id);
    };
    const finish = (result: Record<string, unknown>) => {
      stopResending();
      clearTimeout(timeout);
      pending.delete(id);
      resolve(result);
    };
    const timeout = setTimeout(
      () =>
        finish({
          ok: false,
          error: received
            ? "the canvas started the action but did not finish it in time (the artifact may be busy, or it reloaded)"
            : "the canvas did not receive the action (it may have closed or still be loading)",
        }),
      FRAME_TIMEOUT_MS,
    );
    pending.set(id, finish);
    acks.set(id, stopResending);
    const send = () => {
      // "*" is required for the opaque sandboxed frame; the frame checks event.source.
      // Look the frame up each time: the viewer may have remounted since the last send.
      currentFrame(conversationId)
        ?.getWindow()
        ?.postMessage({ source: CANVAS_REQUEST_SOURCE, type: "canvas-request", id, action, args }, "*");
    };
    send();
    resendTimer = setInterval(send, RESEND_MS);
  });
}

async function claim(conversationId: string, actionId: string): Promise<string | null> {
  try {
    const resp = await authenticatedFetch(
      `/v1/sessions/${encodeURIComponent(conversationId)}/browser/action_claim/${encodeURIComponent(actionId)}`,
      { method: "POST" },
    );
    if (!resp.ok) return null;
    const body = (await resp.json()) as { claimed?: boolean; claim_token?: string };
    return body?.claimed && typeof body.claim_token === "string" ? body.claim_token : null;
  } catch {
    return null;
  }
}

async function postResult(
  conversationId: string,
  actionId: string,
  claimToken: string,
  result: Record<string, unknown>,
): Promise<void> {
  try {
    await authenticatedFetch(
      `/v1/sessions/${encodeURIComponent(conversationId)}/browser/action_result/${encodeURIComponent(actionId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result, claim_token: claimToken }),
      },
    );
  } catch (e) {
    console.warn("[canvas-relay] posting the result failed", e);
  }
}

async function onRequest(evt: BrowserActionRequestEvent, conversationId: string | null) {
  if (!conversationId || !isCanvasAction(evt.action)) return;
  // Only a tab showing this session's canvas claims; others stay out of the race.
  if (!currentFrame(conversationId)) return;
  // Take this action's place in the session's queue now, so actions run in the
  // order they arrived; claim at once (the server waits only briefly for a claim).
  const previous = queues.get(conversationId) ?? Promise.resolve();
  let release = () => {};
  const mine = new Promise<void>((resolve) => {
    release = resolve;
  });
  const tail = previous.then(() => mine);
  queues.set(conversationId, tail);
  try {
    const token = await claim(conversationId, evt.actionId);
    if (!token) return;
    await previous;
    const frame = currentFrame(conversationId);
    const result = frame
      ? await runInFrame(conversationId, evt.action, evt.args ?? {})
      : { ok: false, error: "the canvas closed before the action ran" };
    const shown = currentFrame(conversationId) ?? frame;
    if (shown?.path && typeof result.data === "object" && result.data !== null) {
      (result.data as Record<string, unknown>).path = shown.path;
    }
    await postResult(conversationId, evt.actionId, token, result);
  } finally {
    release();
    void tail.then(() => {
      if (queues.get(conversationId) === tail) queues.delete(conversationId);
    });
  }
}

let started = false;

/** Start listening for canvas actions (idempotent). */
export function ensureCanvasRelay(): void {
  if (started) return;
  started = true;
  // Results are matched by their random request id, so they are accepted from any
  // window: a viewer that remounted mid-action has dropped its own listener.
  window.addEventListener("message", (event) => {
    handleCanvasResult(event.data);
  });
  onBrowserActionRequest((evt, conversationId) => {
    void onRequest(evt, conversationId).catch((e) => console.warn("[canvas-relay]", e));
  });
}
