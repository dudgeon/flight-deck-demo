// omnigent-slim: the comment threads of a markdown document, kept in a sidecar
// file next to it, `<document>.review.json`. Same format as `pa review`
// (skills/view-kit/scripts/docreview.py), so agents read and write it too.

import type { RosterEntry } from "@/lib/participantTurn";

export const SIDECAR_SUFFIX = ".review.json";
export const USER_ID = "you";
export const MAIN_AGENT_ID = "aviator";

export interface ReviewMessage {
  id: string;
  by: string;
  at: string;
  text: string;
  mentions?: string[];
}

export interface ReviewThread {
  id: string;
  anchor: { quote: string; occurrence?: number };
  by: string;
  at: string;
  resolved: boolean;
  resolved_by?: string;
  messages: ReviewMessage[];
}

export interface ReviewFile {
  version: 1;
  threads: ReviewThread[];
  updated?: string;
}

export function sidecarPath(path: string): string {
  return path + SIDECAR_SUFFIX;
}

export function emptyReview(): ReviewFile {
  return { version: 1, threads: [] };
}

export function parseReview(text: string | null | undefined): ReviewFile {
  if (!text) return emptyReview();
  try {
    const data = JSON.parse(text) as Partial<ReviewFile>;
    if (!data || !Array.isArray(data.threads)) return emptyReview();
    return {
      version: 1,
      threads: data.threads.filter((t) => t && t.id && t.anchor),
      updated: data.updated,
    };
  } catch {
    return emptyReview();
  }
}

export function serializeReview(data: ReviewFile): string {
  return JSON.stringify({ ...data, version: 1, updated: new Date().toISOString() }, null, 1) + "\n";
}

function nextId(prefix: string, ids: string[]): string {
  const nums = ids
    .filter((id) => id.startsWith(prefix))
    .map((id) => Number(id.slice(prefix.length)))
    .filter(Number.isFinite);
  return `${prefix}${Math.max(0, ...nums) + 1}`;
}

/** Someone who can write in a document: the user, the main agent, or a participant. */
export interface Author {
  id: string;
  name: string;
  kind: "you" | "main" | "agent" | "person";
  standIn: boolean;
  role: string;
}

export function authorsFrom(roster: RosterEntry[], userName = "You"): Map<string, Author> {
  const map = new Map<string, Author>();
  map.set(USER_ID, { id: USER_ID, name: userName, kind: "you", standIn: false, role: "" });
  map.set(MAIN_AGENT_ID, {
    id: MAIN_AGENT_ID,
    name: "Claude",
    kind: "main",
    standIn: false,
    role: "Your agent in this chat",
  });
  for (const entry of roster) {
    map.set(entry.id, {
      id: entry.id,
      name: entry.name,
      kind: entry.kind,
      standIn: entry.standIn,
      role: entry.role,
    });
  }
  return map;
}

export function authorOf(authors: Map<string, Author>, id: string | null | undefined): Author {
  if (id && authors.has(id)) return authors.get(id)!;
  const name = (id ?? "unknown")
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
  return { id: id ?? "unknown", name, kind: "agent", standIn: false, role: "" };
}

/** Everyone @mentioned in `text`, by id, full name or first name. */
export function resolveMentions(text: string, authors: Map<string, Author>): string[] {
  const byName = new Map<string, string>();
  for (const a of authors.values()) {
    if (a.kind === "you") continue;
    byName.set(a.id.toLowerCase(), a.id);
    byName.set(a.name.toLowerCase(), a.id);
    const first = a.name.split(/\s+/)[0].toLowerCase();
    if (!byName.has(first)) byName.set(first, a.id);
  }
  byName.set("claude", MAIN_AGENT_ID);
  const found: string[] = [];
  for (const match of text.matchAll(/(?<![\w@])@([A-Za-z][\w-]*(?: [A-Z][\w-]*)?)/g)) {
    const raw = match[1].toLowerCase();
    const id = byName.get(raw) ?? byName.get(raw.split(" ")[0]);
    if (id && !found.includes(id)) found.push(id);
  }
  return found;
}

export function addThread(
  data: ReviewFile,
  quote: string,
  text: string,
  mentions: string[],
): ReviewFile {
  const at = new Date().toISOString();
  const thread: ReviewThread = {
    id: nextId(
      "t",
      data.threads.map((t) => t.id),
    ),
    anchor: { quote },
    by: USER_ID,
    at,
    resolved: false,
    messages: [
      {
        id: nextId("m", allMessageIds(data)),
        by: USER_ID,
        at,
        text,
        ...(mentions.length ? { mentions } : {}),
      },
    ],
  };
  return { ...data, threads: [...data.threads, thread] };
}

export function addReply(
  data: ReviewFile,
  threadId: string,
  text: string,
  mentions: string[],
): ReviewFile {
  const id = nextId("m", allMessageIds(data));
  const at = new Date().toISOString();
  return {
    ...data,
    threads: data.threads.map((t) =>
      t.id === threadId
        ? {
            ...t,
            resolved: false,
            messages: [
              ...t.messages,
              { id, by: USER_ID, at, text, ...(mentions.length ? { mentions } : {}) },
            ],
          }
        : t,
    ),
  };
}

export function setResolved(data: ReviewFile, threadId: string, resolved: boolean): ReviewFile {
  return {
    ...data,
    threads: data.threads.map((t) =>
      t.id === threadId
        ? { ...t, resolved, ...(resolved ? { resolved_by: USER_ID } : { resolved_by: undefined }) }
        : t,
    ),
  };
}

export function deleteThread(data: ReviewFile, threadId: string): ReviewFile {
  return { ...data, threads: data.threads.filter((t) => t.id !== threadId) };
}

function allMessageIds(data: ReviewFile): string[] {
  return data.threads.flatMap((t) => t.messages.map((m) => m.id));
}

/** Mentions nobody has answered: no later message in the thread by the one mentioned. */
export function waitingOn(thread: ReviewThread): string[] {
  const waiting: string[] = [];
  thread.messages.forEach((msg, i) => {
    for (const who of msg.mentions ?? []) {
      const answered = thread.messages.slice(i + 1).some((later) => later.by === who);
      if (!answered && !waiting.includes(who)) waiting.push(who);
    }
  });
  return thread.resolved ? [] : waiting;
}

/**
 * The message that asks the main agent to bring the mentioned people in.
 * It names only ids and the thread, so the agent reads the words from the file.
 */
export function routingMessage(
  path: string,
  threadId: string,
  mentions: string[],
  authors: Map<string, Author>,
): string {
  const others = mentions.filter((id) => id !== MAIN_AGENT_ID);
  const names = others.map((id) => `${authorOf(authors, id).name} (${id})`);
  const parts = [
    `I mentioned ${[...names, ...(mentions.includes(MAIN_AGENT_ID) ? ["you"] : [])].join(" and ")} in a comment on \`${path}\`, thread ${threadId}.`,
  ];
  if (others.length) {
    parts.push(
      `Ask ${others.length > 1 ? "each of them" : "them"} to answer in the thread, as in "Comments in documents" in the participants skill: \`pa review ask ${path} ${threadId} <id>\` gives the message to send. Their answers go in the thread, not in this chat; tell me in one line when they have replied.`,
    );
  }
  if (mentions.includes(MAIN_AGENT_ID)) {
    parts.push(
      `Read the thread with \`pa review show ${path}\` and answer it there with \`pa review reply ${path} ${threadId} --by aviator\`.`,
    );
  }
  return parts.join(" ");
}
