// omnigent-slim: text handed to a session's message box from another page.
//
// The project page's Resume button opens the run's session and wants "Resume
// intent shaping..." waiting in the composer for the user to send. The session
// page is not mounted yet when the button is pressed, so the text waits here
// (sessionStorage: this tab only, gone when the tab closes) and the chat page
// takes it once.

const KEY_PREFIX = "omnigent-slim:pending-prompt:";
const MAX_CHARS = 2000;

/** Leave `text` for session `sessionId`'s composer to pick up when it opens. */
export function setPendingPrompt(sessionId: string, text: string): void {
  try {
    window.sessionStorage.setItem(KEY_PREFIX + sessionId, text.slice(0, MAX_CHARS));
  } catch {
    // Storage blocked: the session still opens, without the text.
  }
}

/** The text waiting for `sessionId`, removed as it is read; `null` when none. */
export function takePendingPrompt(sessionId: string): string | null {
  try {
    const key = KEY_PREFIX + sessionId;
    const text = window.sessionStorage.getItem(key);
    if (text !== null) window.sessionStorage.removeItem(key);
    return text || null;
  } catch {
    return null;
  }
}
