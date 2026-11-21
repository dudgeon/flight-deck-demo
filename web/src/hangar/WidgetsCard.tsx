/**
 * omnigent-slim: a workflow's widgets and views, edited in the Hangar (D-114).
 *
 * A widget is a view the agent puts in the chat (a question form, one record's
 * card, a summary); a view is one it opens in the canvas. Both are view-kit
 * specs in the workflow's `views/` folder. Here each one is drawn from the
 * draft over the scenario's sample data, with its header text, questions and
 * buttons editable as fields and the whole spec editable as JSON. The drawing
 * follows every saved change.
 */

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { type HangarView, draftViewPath } from "./hangarApi";
import { Rendered, layoutLabel } from "./parts";

type Spec = Record<string, unknown>;

interface Props {
  workflowId: string;
  /** The draft's save stamp: the drawings reload when it changes. */
  version: string | null;
  views: HangarView[];
  /** The draft's `views` map: name to spec file. */
  manifestViews: Record<string, string>;
  text: (path: string) => string;
  onFile: (path: string, text: string | null) => void;
  onViews: (views: Record<string, string>) => void;
  /** The view named in the address (`#widget-card`), opened on arrival. */
  focus?: string | null;
}

const NAME = /^[a-z0-9][a-z0-9-]{0,40}$/;

function parse(text: string): { spec: Spec | null; error: string | null } {
  try {
    const spec = JSON.parse(text) as unknown;
    if (!spec || typeof spec !== "object" || Array.isArray(spec)) {
      return { spec: null, error: "A view spec is one JSON object, { … }." };
    }
    return { spec: spec as Spec, error: null };
  } catch (err) {
    return { spec: null, error: err instanceof Error ? err.message : String(err) };
  }
}

const asText = (v: unknown) => (typeof v === "string" ? v : "");
const objects = (v: unknown): Spec[] =>
  Array.isArray(v) ? v.filter((x): x is Spec => !!x && typeof x === "object") : [];

/** Starting specs for a new widget or view; each passes `pa check` as it is. */
const BLANK: Record<string, (name: string) => Spec> = {
  form: (name) => ({
    view: name,
    layout: "form",
    eyebrow: "Before we start",
    title: "A question for you",
    fields: [{ id: "answer", label: "Your answer", kind: "line" }],
    submit: { label: "Send", prompt: "{answers}" },
  }),
  summary: (name) => ({
    view: name,
    layout: "summary",
    eyebrow: "Where things stand",
    title: "{dataset.title}",
    blocks: [{ kind: "tiles", tiles: [{ label: "Records", where: {} }] }],
  }),
};

export function WidgetsCard({
  workflowId,
  version,
  views,
  manifestViews,
  text,
  onFile,
  onViews,
  focus,
}: Props) {
  const [open, setOpen] = useState<string | null>(focus ?? null);
  useEffect(() => {
    if (!focus) return;
    setOpen(focus);
    document.getElementById(`widget-${focus}`)?.scrollIntoView({ block: "start" });
  }, [focus]);
  const shown = views.filter((v) => v.name in manifestViews);
  // A view added on this page shows before the draft is saved and read back.
  const pending = Object.keys(manifestViews).filter((n) => !views.some((v) => v.name === n));
  const groups: { host: "chat" | "canvas"; label: string; note: string }[] = [
    {
      host: "chat",
      label: "Widgets · in the chat",
      note: "What the agent puts in the conversation for the person to answer or glance at.",
    },
    {
      host: "canvas",
      label: "Views · in the canvas",
      note: "What the agent opens beside the chat for the person to work in.",
    },
  ];
  return (
    <section id="widgets" className="card editing" data-testid="hangar-widgets">
      <span className="lab">Widgets and views · what people see</span>
      {groups.map((g) => {
        const items = shown.filter((v) => v.host === g.host);
        return (
          <div key={g.host} className="widgets-group">
            <div className="row">
              <b className="text-[13px]">{g.label}</b>
              <span className="lab">{items.length}</span>
            </div>
            <p className="lab">{g.note}</p>
            {items.length === 0 ? (
              <p className="lab">None yet.</p>
            ) : (
              <ul className="widgets">
                {items.map((view) => (
                  <WidgetRow
                    key={view.name}
                    workflowId={workflowId}
                    version={version}
                    view={view}
                    file={manifestViews[view.name]}
                    open={open === view.name}
                    onOpen={() => setOpen(open === view.name ? null : view.name)}
                    text={text}
                    onFile={onFile}
                    onRemove={() => {
                      onViews(
                        Object.fromEntries(
                          Object.entries(manifestViews).filter(([n]) => n !== view.name),
                        ),
                      );
                      onFile(manifestViews[view.name], null);
                      setOpen(null);
                    }}
                  />
                ))}
              </ul>
            )}
          </div>
        );
      })}
      {pending.length > 0 && (
        <p className="lab">Adding {pending.join(", ")}… it shows here once the draft saves.</p>
      )}
      <AddWidget
        views={shown}
        manifestViews={manifestViews}
        text={text}
        onFile={onFile}
        onViews={onViews}
        onAdded={setOpen}
      />
    </section>
  );
}

function WidgetRow({
  workflowId,
  version,
  view,
  file,
  open,
  onOpen,
  text,
  onFile,
  onRemove,
}: {
  workflowId: string;
  version: string | null;
  view: HangarView;
  file: string;
  open: boolean;
  onOpen: () => void;
  text: (path: string) => string;
  onFile: (path: string, text: string | null) => void;
  onRemove: () => void;
}) {
  const saved = text(file);
  // What is typed in the JSON box; only valid JSON is saved to the draft.
  const [typed, setTyped] = useState<string | null>(null);
  const raw = typed ?? saved;
  const { spec, error } = parse(raw);
  const [showJson, setShowJson] = useState(false);
  useEffect(() => {
    if (typed !== null && typed === saved) setTyped(null);
  }, [typed, saved]);
  const chat = view.host === "chat";
  /** Change one part of the spec and write the file back. */
  const update = (fn: (s: Spec) => void) => {
    if (!spec) return;
    const next = structuredClone(spec);
    fn(next);
    setTyped(null);
    onFile(file, `${JSON.stringify(next, null, 1)}\n`);
  };
  return (
    <li
      id={`widget-${view.name}`}
      className={cn("widget", open && "on")}
      data-testid="hangar-widget"
    >
      <div className="row">
        <button type="button" className="filename" onClick={onOpen} aria-expanded={open}>
          {view.title}
        </button>
        <span className="chip">{layoutLabel(view.layout)}</span>
        {view.actions > 0 && (
          <span className="lab">
            {view.actions} button{view.actions === 1 ? "" : "s"}
          </span>
        )}
        <span className="sp" />
        <span className="path">{file}</span>
        <button
          type="button"
          className="del"
          aria-label={`Remove ${view.title}`}
          title="Remove it from the workflow"
          onClick={onRemove}
        >
          ×
        </button>
      </div>
      {open && (
        <div className="widget-edit">
          <div className="flex min-w-0 flex-col gap-2">
            {spec ? (
              <SpecFields spec={spec} update={update} />
            ) : (
              <p className="lab">Fix the JSON below to edit the fields.</p>
            )}
            <button
              type="button"
              className="linkish link self-start text-xs"
              onClick={() => setShowJson(!showJson)}
            >
              {showJson ? "Hide" : "Show"} the whole spec (JSON)
            </button>
            {(showJson || !spec) && (
              <textarea
                className="hangar-input brief"
                value={raw}
                onChange={(e) => {
                  setTyped(e.target.value);
                  if (!parse(e.target.value).error) onFile(file, e.target.value);
                }}
                spellCheck={false}
                aria-label={file}
                data-testid="hangar-widget-json"
              />
            )}
            {error && <p className="lab x">Not valid JSON yet, so not saved: {error}</p>}
            <p className="lab">
              Shown {chat ? "in the chat" : "in the canvas"}, as the instructions or the scenario's
              script place it. Every key is in the view-kit's spec reference.
            </p>
          </div>
          <div className="min-w-0" style={chat ? { maxWidth: 720 } : undefined}>
            <Rendered
              path={`${draftViewPath(workflowId, view.name)}?v=${encodeURIComponent(version ?? "")}`}
              title={`${view.title}: as the draft draws it`}
              height={chat ? 460 : 560}
              host={view.host}
            />
            <p className="lab">
              The draft, over the scenario's sample data. Buttons do nothing here.
            </p>
          </div>
        </div>
      )}
    </li>
  );
}

/** The parts of a spec people change most, as plain fields. */
function SpecFields({ spec, update }: { spec: Spec; update: (fn: (s: Spec) => void) => void }) {
  const actions = objects(spec.actions);
  const fields = spec.layout === "form" ? objects(spec.fields) : [];
  const submit = spec.submit && typeof spec.submit === "object" ? (spec.submit as Spec) : null;
  const line = (key: "eyebrow" | "title" | "subtitle", label: string, hint: string) => (
    <label className="field">
      <span>{label}</span>
      <input
        className="hangar-input"
        value={asText(spec[key])}
        placeholder={hint}
        onChange={(e) =>
          update((s) => {
            // An empty line leaves the key out rather than drawing an empty header.
            s[key] = e.target.value || undefined;
          })
        }
        data-testid={`hangar-widget-${key}`}
      />
    </label>
  );
  return (
    <>
      {line("eyebrow", "Small line above", "e.g. A decision for you")}
      {line("title", "Heading", "{dataset.title} puts in the dataset's name")}
      {line("subtitle", "Line under the heading", "Optional")}
      {fields.length > 0 && (
        <div className="field">
          <span>Questions</span>
          {fields.map((f, i) => (
            <input
              // oxlint-disable-next-line react/no-array-index-key -- questions are edited in place by position
              key={i}
              className="hangar-input"
              value={asText(f.label)}
              aria-label={`Question ${i + 1}`}
              onChange={(e) =>
                update((s) => {
                  objects(s.fields)[i].label = e.target.value;
                })
              }
            />
          ))}
        </div>
      )}
      {(actions.length > 0 || submit) && (
        <div className="field">
          <span>Buttons (what the person can press)</span>
          {submit && (
            <ButtonFields
              label={asText(submit.label)}
              prompt={asText(submit.prompt)}
              onLabel={(v) =>
                update((s) => {
                  (s.submit as Spec).label = v;
                })
              }
              onPrompt={(v) =>
                update((s) => {
                  (s.submit as Spec).prompt = v;
                })
              }
            />
          )}
          {actions.map((a, i) => (
            <ButtonFields
              // oxlint-disable-next-line react/no-array-index-key -- buttons are edited in place by position
              key={i}
              label={asText(a.label)}
              prompt={asText(a.prompt)}
              id={asText(a.id)}
              onLabel={(v) =>
                update((s) => {
                  objects(s.actions)[i].label = v;
                })
              }
              onPrompt={(v) =>
                update((s) => {
                  const act = objects(s.actions)[i];
                  if (v) act.prompt = v;
                  else delete act.prompt;
                })
              }
            />
          ))}
        </div>
      )}
    </>
  );
}

function ButtonFields({
  label,
  prompt,
  id,
  onLabel,
  onPrompt,
}: {
  label: string;
  prompt: string;
  id?: string;
  onLabel: (v: string) => void;
  onPrompt: (v: string) => void;
}) {
  return (
    <div className="widget-button">
      <input
        className="hangar-input"
        value={label}
        onChange={(e) => onLabel(e.target.value)}
        aria-label={`Button label${id ? ` (${id})` : ""}`}
        placeholder="Button label"
      />
      <input
        className="hangar-input"
        value={prompt}
        onChange={(e) => onPrompt(e.target.value)}
        aria-label={`What pressing ${label || "it"} says in the chat`}
        placeholder="What pressing it says in the chat (optional)"
      />
      {id && <span className="lab">id {id} · the instructions say what the agent does</span>}
    </div>
  );
}

function AddWidget({
  views,
  manifestViews,
  text,
  onFile,
  onViews,
  onAdded,
}: {
  views: HangarView[];
  manifestViews: Record<string, string>;
  text: (path: string) => string;
  onFile: (path: string, text: string | null) => void;
  onViews: (views: Record<string, string>) => void;
  onAdded: (name: string) => void;
}) {
  const [name, setName] = useState("");
  const [from, setFrom] = useState("blank:form");
  const [host, setHost] = useState<"chat" | "canvas">("chat");
  const id = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  const taken = id in manifestViews;
  const valid = NAME.test(id) && !taken;
  const add = () => {
    let spec: Spec;
    if (from.startsWith("blank:")) {
      spec = BLANK[from.slice(6)](id);
    } else {
      const source = parse(text(manifestViews[from])).spec ?? {};
      spec = { ...structuredClone(source), view: id };
    }
    const path = `views/${id}.json`;
    onFile(path, `${JSON.stringify(spec, null, 1)}\n`);
    onViews({ ...manifestViews, [id]: path });
    // Tell the agent when to show it: this line is also what places it.
    const skill = text("SKILL.md").replace(/\s*$/, "\n");
    const how =
      host === "chat"
        ? `\`$PA render SKILL_DIR/${path} --host chat --data <dataset> --out artifacts/<slug>-${id}.html\` and put the printed view block in your reply`
        : `\`$PA render SKILL_DIR/${path} --data <dataset> --out artifacts/<slug>-${id}.html\`, then open the file`;
    onFile(
      "SKILL.md",
      `${skill}\n## The ${id} ${host === "chat" ? "widget" : "view"}\n\nWhen to show it: (say when). Draw it with ${how}.\n`,
    );
    onAdded(id);
    setName("");
  };
  return (
    <form
      className="widgets-add"
      onSubmit={(e) => {
        e.preventDefault();
        if (valid) add();
      }}
    >
      <span className="lab">Add a widget or view</span>
      <div className="row">
        <input
          className="hangar-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name, e.g. scope-check"
          aria-label="New widget name"
          data-testid="hangar-widget-name"
        />
        <select
          className="hangar-input"
          value={from}
          onChange={(e) => {
            setFrom(e.target.value);
            const v = views.find((x) => x.name === e.target.value);
            if (v) setHost(v.host);
            else setHost(e.target.value === "blank:form" ? "chat" : host);
          }}
          aria-label="Start from"
        >
          <option value="blank:form">A blank question form</option>
          <option value="blank:summary">A blank summary</option>
          {views.map((v) => (
            <option key={v.name} value={v.name}>
              A copy of {v.title}
            </option>
          ))}
        </select>
        <select
          className="hangar-input"
          value={host}
          onChange={(e) => setHost(e.target.value as "chat" | "canvas")}
          aria-label="Where it shows"
        >
          <option value="chat">In the chat</option>
          <option value="canvas">In the canvas</option>
        </select>
        <button
          type="submit"
          className="hangar-btn"
          disabled={!valid}
          data-testid="hangar-widget-add"
        >
          Add
        </button>
      </div>
      {taken && <p className="lab x">This workflow already has one called {id}.</p>}
      <p className="lab">
        Adding also writes a line in the instructions telling the agent how to show it. Say there
        when it should.
      </p>
    </form>
  );
}
