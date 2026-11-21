// omnigent-slim: whether a Review panel is open in a markdown editor, so the
// app shell can widen the right rail (taking room from chat) and, when chat
// would get too thin, collapse the left sidebar. Same idea as upstream's
// `fileViewerCommentsOpen`, but without threading a prop through every viewer.

import { useSyncExternalStore } from "react";

/** The review panel's width (Tailwind w-80). */
export const REVIEW_PANEL_WIDTH_PX = 320;
/** Room the document keeps beside the review panel. */
export const REVIEW_DOCUMENT_MIN_PX = 440;
/** The narrowest the rail may be while a review panel is open. */
export const REVIEW_RAIL_MIN_PX = REVIEW_PANEL_WIDTH_PX + REVIEW_DOCUMENT_MIN_PX;

const open = new Set<symbol>();
const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

/** Record that one review panel is open (true) or closed/unmounted (false). */
export function setReviewPanelOpen(id: symbol, isOpen: boolean): void {
  const had = open.has(id);
  if (isOpen === had) return;
  if (isOpen) open.add(id);
  else open.delete(id);
  emit();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** True while any review panel is open. */
export function useReviewPanelOpen(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => open.size > 0,
    () => false,
  );
}

/** Chat's minimum width beside the rail (upstream's CHAT_MIN_WIDTH_PX). */
export const REVIEW_CHAT_MIN_PX = 480;
