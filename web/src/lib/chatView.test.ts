import { describe, expect, it } from "vitest";
import { chatViewHeight, parseChatView, prepareChatView } from "./chatView";

describe("parseChatView", () => {
  it("reads the file and title", () => {
    expect(parseChatView("file: artifacts/x-card.html\ntitle: Pick one")).toEqual({
      file: "artifacts/x-card.html",
      title: "Pick one",
    });
  });

  it("accepts a leading ./ and no title", () => {
    expect(parseChatView("file: ./artifacts/x.html")).toEqual({ file: "artifacts/x.html", title: null });
  });

  it("refuses paths outside the workspace and files that are not views", () => {
    expect(parseChatView("file: /etc/passwd.html")).toBeNull();
    expect(parseChatView("file: artifacts/../../secret.html")).toBeNull();
    expect(parseChatView("file: data/x.json")).toBeNull();
    expect(parseChatView("title: nothing")).toBeNull();
  });
});

describe("chatViewHeight", () => {
  it("reads only the kit's size message", () => {
    expect(chatViewHeight({ source: "pa-kit", type: "size", height: 312 })).toBe(312);
    expect(chatViewHeight({ source: "pa-kit", type: "size", height: "312" })).toBeNull();
    expect(chatViewHeight({ source: "other", type: "size", height: 1 })).toBeNull();
    expect(chatViewHeight(null)).toBeNull();
  });
});

describe("prepareChatView", () => {
  it("marks the host as chat right after the doctype", () => {
    const html = prepareChatView("<!doctype html><html><body>x</body></html>");
    expect(html.startsWith("<!doctype html><script data-omnigent-chat-view>")).toBe(true);
    expect(html).toContain('setAttribute("data-host", "chat")');
  });
});
