// omnigent-slim: a run card the director draws in its chat (D-89, D-116).
//
// Aviator directs a project and starts each workflow in a thread of its own.
// So the person can see that work without leaving the director, Aviator names
// the run's progress file in a fenced block:
//
//   ```run
//   file: progress/teen-allowances-intent--intent-shaping.json
//   title: Intent shaping: Teen allowances
//   session: 4f0c2d…        (the thread, so the card can open it before the file exists)
//   ```
//
// The chat draws a live card from that file: the step, the state, what the
// thread last reported, and a way into the thread. The file is written by
// `pa flow` and `pa report` in the thread; the card only reads it.

/** The fence language that marks a run card. */
export const RUN_BLOCK_LANGUAGE = "run";

export interface RunBlock {
  /** Workspace-relative path of the run's progress file. */
  file: string;
  /** Shown until the file exists. */
  title: string | null;
  /** The thread's session id, when the director gave it. */
  sessionId: string | null;
}

// Only progress files, inside the workspace: no absolute paths, no "..".
const RUN_FILE = /^progress\/[A-Za-z0-9_][A-Za-z0-9_.-]{0,160}\.json$/;
const SESSION_ID = /^[A-Za-z0-9_-]{6,80}$/;

/**
 * Read a ```run fence.
 *
 * @param text The fence's content.
 * @returns The block, or null when it names no progress file.
 */
export function parseRunBlock(text: string): RunBlock | null {
  let file: string | null = null;
  let title: string | null = null;
  let session = "";
  for (const line of text.split("\n")) {
    const match = /^\s*([a-z_]+)\s*:\s*(.*?)\s*$/.exec(line);
    if (!match) continue;
    if (match[1] === "file") file = match[2].replace(/^\.\//, "");
    if (match[1] === "title") title = match[2].slice(0, 160) || null;
    if (match[1] === "session") session = match[2];
  }
  if (!file || !RUN_FILE.test(file) || file.includes("..")) return null;
  return { file, title, sessionId: SESSION_ID.test(session) ? session : null };
}

/** "progress/a--b.json" as the run id "a--b". */
export function runIdOfFile(file: string): string {
  return file.replace(/^progress\//, "").replace(/\.json$/, "");
}
