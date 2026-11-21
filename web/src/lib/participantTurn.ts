// omnigent-slim: a turn spoken by someone other than the session's own agent.
//
// The agent hosts other agents and people in the conversation (see the
// `participants` skill). It passes on what one of them said as a fenced block:
//
//   ```participant
//   name: Risk Review
//   kind: agent
//   role: Risk and compliance
//   session: 4f0c2d…        (optional: the background session that plays them)
//   ---
//   Their reply, word for word.
//   ```
//
// The chat draws that block as the participant's own turn. The header is a
// display label written by the agent, not proof of who spoke.

export const PARTICIPANT_LANGUAGE = "participant";

export interface ParticipantTurn {
  name: string;
  /** "agent", or "person" for a human. */
  kind: "agent" | "person";
  role: string;
  /** A person played by an agent. Always shown, so nobody mistakes it for the real person. */
  standIn: boolean;
  /** The session speaking for them, when there is one. */
  sessionId: string | null;
  body: string;
}

const HEADER_LINE = /^([a-z_]+):[ \t]*(.*)$/;
const SESSION_ID = /^[A-Za-z0-9_-]{6,80}$/;
const MAX_HEADER_LINES = 8;

/**
 * Read a participant block's text.
 *
 * :param code: The text inside the fence, e.g. ``"name: Mara\nkind: person\n---\nHi"``.
 * :returns: The turn, or ``null`` when the text has no header naming someone.
 */
export function parseParticipantTurn(code: string): ParticipantTurn | null {
  const lines = code.replace(/\r\n/g, "\n").split("\n");
  const end = lines.findIndex((line) => line.trim() === "---");
  if (end < 1 || end > MAX_HEADER_LINES) return null;
  const header: Record<string, string> = {};
  for (const line of lines.slice(0, end)) {
    const match = HEADER_LINE.exec(line.trim());
    if (!match) return null;
    header[match[1]] = match[2].trim();
  }
  const name = (header.name ?? "").slice(0, 60);
  if (!name) return null;
  const kind = header.kind === "person" ? "person" : "agent";
  const session = header.session ?? "";
  return {
    name,
    kind,
    role: (header.role ?? "").slice(0, 80),
    // A person in this chat is only ever played by an agent unless the header says otherwise.
    standIn: kind === "person" ? header.stand_in !== "false" : header.stand_in === "true",
    sessionId: SESSION_ID.test(session) ? session : null,
    body: lines
      .slice(end + 1)
      .join("\n")
      .trim(),
  };
}

/** "Mara Okafor" as "MO". */
export function participantInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join("");
}

/** One participant file's header: what the Session panel lists. */
export interface RosterEntry {
  id: string;
  name: string;
  kind: "agent" | "person";
  role: string;
  standIn: boolean;
  backing: string;
  callFor: string;
}

/**
 * Read the header of a ``participants/<id>.md`` file.
 *
 * :param id: The file's name without ``.md``, e.g. ``"risk-review"``.
 * :param text: The file's text.
 */
export function parseRosterEntry(id: string, text: string): RosterEntry {
  const header: Record<string, string> = {};
  const normalized = text.replace(/\r\n/g, "\n");
  if (normalized.startsWith("---\n")) {
    const end = normalized.indexOf("\n---", 4);
    for (const line of normalized.slice(4, end === -1 ? undefined : end).split("\n")) {
      const match = HEADER_LINE.exec(line.replace(/\s+#.*$/, "").trim());
      if (match) header[match[1]] = match[2].trim().replace(/^"(.*)"$/, "$1");
    }
  }
  const kind = header.kind === "person" ? "person" : "agent";
  const fallback = id
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
  return {
    id,
    name: header.name || fallback,
    kind,
    role: header.role ?? "",
    standIn: kind === "person" ? header.stand_in !== "false" : header.stand_in === "true",
    backing: header.backing === "script" ? "script" : "session",
    callFor: header.call_for ?? "",
  };
}
