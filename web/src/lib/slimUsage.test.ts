import { afterEach, describe, expect, it, vi } from "vitest";
import type { authenticatedFetch } from "./identity";
import { flushSlimUsage, pendingSlimUsage, slimUsageSink } from "./slimUsage";

describe("slimUsage", () => {
  afterEach(() => {
    flushSlimUsage(vi.fn().mockResolvedValue(new Response()) as unknown as typeof authenticatedFetch);
  });

  it("queues events with the page's path and posts them in one batch", () => {
    slimUsageSink({ type: "page_view", pageId: "library" });
    slimUsageSink({ type: "click", componentId: "hangar.publish", componentKind: "button" });
    expect(pendingSlimUsage()).toHaveLength(2);
    expect(pendingSlimUsage()[0].path).toBeDefined();

    const send = vi.fn().mockResolvedValue(new Response());
    expect(flushSlimUsage(send as unknown as typeof authenticatedFetch)).toBe(2);
    expect(send).toHaveBeenCalledTimes(1);
    const [url, init] = send.mock.calls[0];
    expect(String(url)).toContain("/v1/slim/usage/events");
    const body = JSON.parse(init.body);
    expect(body.events.map((e: { type: string }) => e.type)).toEqual(["page_view", "click"]);
    expect(pendingSlimUsage()).toHaveLength(0);
  });

  it("sends nothing when nothing is queued", () => {
    const send = vi.fn();
    expect(flushSlimUsage(send as unknown as typeof authenticatedFetch)).toBe(0);
    expect(send).not.toHaveBeenCalled();
  });

  it("never throws when sending fails", () => {
    slimUsageSink({ type: "page_view", pageId: "hangar" });
    const send = vi.fn(() => {
      throw new Error("offline");
    });
    expect(() => flushSlimUsage(send as unknown as typeof authenticatedFetch)).not.toThrow();
  });
});
