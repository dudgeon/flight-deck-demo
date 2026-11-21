/**
 * omnigent-slim: send the app's analytics events to the local usage log
 * (D-122 to D-127).
 *
 * Upstream already instruments the app for analytics through a host sink
 * (`OmnigentHostConfig.analytics`, see `lib/host.ts` and `lib/analytics.ts`):
 * page views, clicks and timed interactions, each keyed by a stable id, with
 * field values redacted unless the call site declares them PII-free. Upstream
 * ships no sink, so standalone it records nothing. This file is our sink: it
 * batches those events and posts them to the app's own server
 * (`POST /v1/slim/usage/events`), which writes them to `logs/usage/`.
 * Nothing leaves the machine.
 */

import type { OmnigentAnalyticsEvent } from "@/lib/host";
import { stripBasePath, withBasePath } from "@/lib/basePath";
import { authenticatedFetch } from "@/lib/identity";

const ENDPOINT = "/v1/slim/usage/events";
const FLUSH_MS = 5000;
const MAX_BATCH = 50;

export type SlimUsageEvent = OmnigentAnalyticsEvent & { path?: string };

let queue: SlimUsageEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let listening = false;

/** The page's path without the base path, e.g. `/c/conv_123` or `/hangar/people`. */
export function currentPath(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return stripBasePath(window.location.pathname);
}

/** Take one event from upstream's analytics emitters. Never throws. */
export function slimUsageSink(event: OmnigentAnalyticsEvent): void {
  try {
    queue.push({ ...event, path: currentPath() });
    if (queue.length >= MAX_BATCH) {
      flushSlimUsage();
    } else if (timer === null) {
      timer = setTimeout(flushSlimUsage, FLUSH_MS);
    }
    if (!listening && typeof window !== "undefined") {
      listening = true;
      window.addEventListener("pagehide", () => flushSlimUsage());
    }
  } catch {
    // The usage log must never get in the way.
  }
}

/** Send what is queued. `keepalive` lets the last batch out as the page closes. */
export function flushSlimUsage(send: typeof authenticatedFetch = authenticatedFetch): number {
  if (timer !== null) {
    clearTimeout(timer);
    timer = null;
  }
  const events = queue;
  queue = [];
  if (events.length === 0) return 0;
  try {
    void send(withBasePath(ENDPOINT), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
      keepalive: true,
      credentials: "same-origin",
    }).catch(() => undefined);
  } catch {
    // ignore
  }
  return events.length;
}

/** For tests: what is waiting to be sent. */
export function pendingSlimUsage(): readonly SlimUsageEvent[] {
  return queue;
}
