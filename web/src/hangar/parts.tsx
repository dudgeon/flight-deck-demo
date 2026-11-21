/**
 * omnigent-slim: small parts shared by the Hangar pages and editors.
 */

import { type ReactNode, useMemo } from "react";
import { useResolvedThemeMode } from "@/components/theme/useResolvedThemeMode";
import { injectDesignTokens } from "@/lib/artifactBridge";
import { Link } from "@/lib/routing";
import { cn } from "@/lib/utils";
import { hangarPath, lineDiff, useHangarPage } from "./hangarApi";

export const SHELF_LABELS: Record<string, string> = {
  people: "People and agents",
  workflows: "Workflows",
  views: "Views",
  scenarios: "Scenarios",
  skills: "Skills",
  starters: "Starters",
  frameworks: "Frameworks",
};

export const layoutLabel = (layout: string) =>
  ({ "tree-table": "Table", board: "Board", detail: "Card", form: "Form", summary: "Summary" })[
    layout
  ] ?? layout;
export const hostLabel = (host: string) => (host === "chat" ? "in the chat" : "in the canvas");

export function Checks({ problems, passed }: { problems: string[]; passed: string }) {
  return (
    <ul className="checks" data-testid="hangar-checks">
      {problems.length === 0 ? (
        <li>{passed}</li>
      ) : (
        problems.map((p) => (
          <li key={p} className="x">
            {p}
          </li>
        ))
      )}
    </ul>
  );
}

export function Crumb({ shelf, label }: { shelf: string; label: string }) {
  const name = SHELF_LABELS[shelf] ?? shelf;
  return (
    <div className="crumb">
      <Link to={hangarPath.shelf(shelf)}>{name}</Link>
      <span aria-hidden="true">/</span>
      <span>{label}</span>
    </div>
  );
}

export function Section({
  title,
  children,
  aside,
}: {
  title: string;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <section className="card">
      <div className="row">
        <span className="lab">{title}</span>
        {aside && <span className="sp" />}
        {aside}
      </div>
      {children}
    </section>
  );
}

export function Links({
  items,
  empty,
}: {
  items: { to: string; label: string; note?: string }[];
  empty: string;
}) {
  if (items.length === 0) return <p className="lab">{empty}</p>;
  return (
    <ul className="plain">
      {items.map((item) => (
        <li key={item.to}>
          <Link className="link" to={item.to}>
            {item.label}
          </Link>
          {item.note && <span className="lab"> · {item.note}</span>}
        </li>
      ))}
    </ul>
  );
}

export function Rendered({
  path,
  title,
  height,
  thumb,
  host = "canvas",
}: {
  path: string;
  title: string;
  height?: number;
  thumb?: boolean;
  host?: "canvas" | "chat";
}) {
  const { data, error } = useHangarPage(path);
  const mode = useResolvedThemeMode() === "dark" ? "dark" : "light";
  const srcDoc = useMemo(() => (data ? injectDesignTokens(data, mode) : null), [data, mode]);
  return (
    <div
      className={cn("frame", thumb && "thumb", thumb && host === "chat" && "chat")}
      style={height ? { height } : undefined}
      data-testid="hangar-rendered"
    >
      {error && <p className="empty">{String(error)}</p>}
      {srcDoc && (
        <iframe
          title={title}
          srcDoc={srcDoc}
          // Scripts only: the page cannot reach the app, its storage or the network.
          sandbox="allow-scripts"
          loading="lazy"
          tabIndex={thumb ? -1 : undefined}
          aria-hidden={thumb ? true : undefined}
          style={height && !thumb ? { height } : undefined}
        />
      )}
    </div>
  );
}

export function Diff({ before, after }: { before: string; after: string }) {
  const all = lineDiff(before, after).map((row, line) => ({ ...row, line }));
  const changed = (i: number) => all[i] !== undefined && all[i].op !== "same";
  // Changed lines, with one line of context either side.
  const rows = all.filter((r, i) => r.op !== "same" || changed(i - 1) || changed(i + 1));
  if (!rows.some((r) => r.op !== "same")) return <p className="lab">No changes yet.</p>;
  return (
    <pre className="text diff" data-testid="hangar-diff">
      {rows.map((row) => (
        <span key={row.line} className={row.op}>
          {row.op === "add" ? "+ " : row.op === "del" ? "− " : "  "}
          {row.text}
          {"\n"}
        </span>
      ))}
    </pre>
  );
}

export function ActionError({ error }: { error: unknown }) {
  return error ? (
    <p className="chip fail">{error instanceof Error ? error.message : String(error)}</p>
  ) : null;
}
