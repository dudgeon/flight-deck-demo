/**
 * omnigent-slim: build scenarios and workflows in the Hangar (slice 3, D-71 to D-73).
 *
 * The same pattern as people (D-63): the page is the editor and saves to a
 * draft as you type; Aviator helps from the pop-over; Publish is the gate. A
 * draft here is a copy of the whole folder, so besides the fields every text
 * file in it (the script, fixtures, SKILL.md, context/ and cast/ notes) can be
 * opened and edited in place.
 */

import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "@/lib/routing";
import { cn } from "@/lib/utils";
import { AviatorPopover } from "./AviatorPopover";
import { WidgetsCard } from "./WidgetsCard";
import { ActionError, Checks, Crumb, Diff, Links, Rendered, Section } from "./parts";
import {
  type FolderDraft,
  type FolderEdit,
  type FolderFile,
  type FolderKind,
  type FolderVersion,
  type Hangar,
  folderAviatorPrompt,
  folderPreviewPath,
  hangarPath,
  playPrompt,
  useFolderActions,
  useFolderDraft,
} from "./hangarApi";

type SaveState = "idle" | "saving" | "saved" | "error";

interface Form {
  title: string;
  summary: string;
  opening: string;
  workflow: string;
  participants: string[];
  steps: string[];
  /** A workflow's widgets and views: name to spec file (D-112). */
  views: Record<string, string>;
  /** Text files changed on the page and not yet saved, by path; null deletes. */
  files: Record<string, string | null>;
}

const str = (v: unknown) => (typeof v === "string" ? v : "");
const list = (v: unknown) =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
const viewMap = (v: unknown): Record<string, string> =>
  v && typeof v === "object" && !Array.isArray(v)
    ? Object.fromEntries(
        Object.entries(v as Record<string, unknown>).filter(
          (e): e is [string, string] => typeof e[1] === "string",
        ),
      )
    : {};

function formOf(draft: FolderDraft): Form {
  const m = draft.manifest;
  return {
    title: str(m.title),
    summary: str(m.summary),
    opening: str(m.opening),
    workflow: str(m.workflow),
    participants: list(m.participants),
    steps: list(m.steps),
    views: viewMap(m.views),
    files: {},
  };
}

/** What changed between the saved draft and the form, as one PATCH. */
function editOf(draft: FolderDraft, form: Form): FolderEdit {
  const before = formOf(draft);
  const manifest: Record<string, unknown> = {};
  const keys =
    draft.kind === "scenario"
      ? (["title", "summary", "opening", "workflow", "participants"] as const)
      : (["title", "summary", "steps", "participants", "views"] as const);
  for (const key of keys) {
    if (JSON.stringify(form[key]) !== JSON.stringify(before[key])) {
      manifest[key] = key === "opening" && !form.opening ? null : form[key];
    }
  }
  const edit: FolderEdit = {};
  if (Object.keys(manifest).length > 0) edit.manifest = manifest;
  if (Object.keys(form.files).length > 0) edit.files = form.files;
  return edit;
}

const NOUN = { scenario: "scenario", workflow: "workflow" } as const;
const SHELF = { scenario: "scenarios", workflow: "workflows" } as const;
const ACTION_LABEL = { new: "New", change: "Change", remove: "Removal" } as const;

export function FolderDraftPage({
  hangar,
  kind,
  id,
}: {
  hangar: Hangar;
  kind: FolderKind;
  id: string;
}) {
  const { data, error } = useFolderDraft(kind, id);
  if (error) return <p className="empty">{String(error)}</p>;
  if (!data) return <p className="empty">Opening the draft…</p>;
  if (data.action === "remove") return <RemovalPage draft={data} />;
  return <FolderEditor key={`${kind}/${id}`} hangar={hangar} draft={data} />;
}

function livePath(kind: FolderKind, id: string) {
  return kind === "scenario" ? hangarPath.scenario(id) : hangarPath.workflow(id);
}

function RemovalPage({ draft }: { draft: FolderDraft }) {
  const navigate = useNavigate();
  const { publish, discard } = useFolderActions();
  const [summary, setSummary] = useState("");
  return (
    <>
      <Crumb shelf={SHELF[draft.kind]} label={draft.id} />
      <div className="row">
        <h1>Remove {draft.id}</h1>
        <span className="chip build">Removal · draft</span>
      </div>
      <p className="sub">
        {draft.shipped
          ? "This removes the workspace copy. The version that ships with the app takes over again."
          : `Publishing takes this ${NOUN[draft.kind]} away. The version removed is kept in History.`}
      </p>
      <Section title="Checks">
        <Checks problems={draft.problems} passed="Nothing depends on it." />
      </Section>
      <div className="row">
        <input
          className="hangar-input"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="One line on why (kept in History)"
          aria-label="Why"
        />
        <button
          type="button"
          className="hangar-btn pri"
          disabled={draft.problems.length > 0 || publish.isPending}
          onClick={() =>
            publish.mutate(
              { kind: draft.kind, id: draft.id, summary: summary || "removed" },
              { onSuccess: () => navigate(hangarPath.shelf(SHELF[draft.kind])) },
            )
          }
        >
          Publish the removal
        </button>
        <button
          type="button"
          className="hangar-btn quiet"
          onClick={() =>
            discard.mutate(
              { kind: draft.kind, id: draft.id },
              { onSuccess: () => navigate(livePath(draft.kind, draft.id)) },
            )
          }
        >
          Keep it
        </button>
      </div>
      <ActionError error={publish.error ?? discard.error} />
    </>
  );
}

function FolderEditor({ hangar, draft }: { hangar: Hangar; draft: FolderDraft }) {
  const navigate = useNavigate();
  const { edit, publish, discard } = useFolderActions();
  const [form, setForm] = useState<Form>(() => formOf(draft));
  const [summary, setSummary] = useState("");
  const [save, setSave] = useState<SaveState>("idle");
  const [pinned, setPinned] = useState(false);
  const scriptPath = str(draft.manifest.script) || "script.md";
  const mainFile = draft.kind === "scenario" ? scriptPath : "SKILL.md";
  const [openFile, setOpenFile] = useState<string | null>(null);
  const dirty = useRef(false);
  const known = useRef(draft.updated);
  const current = useRef(draft);
  current.current = draft;

  // Aviator (or a skill) changed the draft: show it, unless an edit is in flight.
  useEffect(() => {
    if (draft.updated !== known.current && !dirty.current) setForm(formOf(draft));
    known.current = draft.updated;
  }, [draft]);

  function change(patch: Partial<Form>) {
    dirty.current = true;
    setForm((f) => ({ ...f, ...patch }));
  }
  function setFile(path: string, text: string | null) {
    dirty.current = true;
    setForm((f) => ({ ...f, files: { ...f.files, [path]: text } }));
  }

  const editMutate = edit.mutateAsync;
  useEffect(() => {
    if (!dirty.current) return;
    setSave("saving");
    const timer = window.setTimeout(() => {
      const draftNow = current.current;
      const patch = editOf(draftNow, form);
      if (!patch.manifest && !patch.files) {
        dirty.current = false;
        setSave("idle");
        return;
      }
      editMutate({ kind: draftNow.kind, id: draftNow.id, edit: patch })
        .then((saved) => {
          known.current = saved.updated;
          // Typing that arrived while this saved stays in the form for the next save.
          setForm((f) => {
            if (f !== form) return f;
            dirty.current = false;
            return formOf(saved);
          });
          setSave("saved");
        })
        .catch(() => setSave("error"));
    }, 700);
    return () => window.clearTimeout(timer);
  }, [form, editMutate]);

  const fileText = (path: string): string => {
    if (path in form.files) return form.files[path] ?? "";
    return draft.files.find((f) => f.path === path)?.text ?? "";
  };
  const isNew = draft.action === "new";
  const blocked = draft.problems.length > 0 || save === "saving";
  const noun = NOUN[draft.kind];
  const title = form.title || draft.id;
  const workflow = hangar.workflows.find((w) => w.id === form.workflow);
  const changed = draft.files.filter((f) => f.change !== "same");
  const viewFiles = new Set(draft.kind === "workflow" ? Object.values(form.views) : []);
  const others = draft.files.filter(
    (f) => f.path !== draft.manifest_file && f.path !== mainFile && !viewFiles.has(f.path),
  );
  const focus = window.location.hash.startsWith("#widget-")
    ? decodeURIComponent(window.location.hash.slice(8))
    : null;

  return (
    <div className={cn("editor", pinned && "with-aviator")} data-testid="hangar-folder-editor">
      <Crumb shelf={SHELF[draft.kind]} label={title} />
      <div className="row">
        <h1>{title}</h1>
        <span className="chip build">
          {ACTION_LABEL[draft.action]} · {noun} draft
        </span>
        {draft.problems.length > 0 ? (
          <span className="chip fail">✕ {draft.problems.length} to fix before publishing</span>
        ) : (
          <span className="chip ok">✓ Ready to publish</span>
        )}
        <span className="sp" />
        <span className="lab" aria-live="polite" data-testid="hangar-saved">
          {save === "saving"
            ? "Saving…"
            : save === "saved"
              ? "Draft saved"
              : save === "error"
                ? "Not saved: check the field marked in the checks"
                : ""}
        </span>
      </div>
      <p className="sub">
        {draft.builtin
          ? `This ${noun} ships with the app. Publishing makes a workspace copy that takes over its id; removing the copy later brings the shipped one back.`
          : `Edits save to this draft as you type. Nobody flying sees them until you publish, and sessions already running keep what they started with.`}
      </p>
      <div className="halves">
        <div className="flex flex-col gap-3.5">
          <section className="card editing">
            <span className="lab">What it is</span>
            <label className="field">
              <span>Title</span>
              <input
                className="hangar-input"
                value={form.title}
                onChange={(e) => change({ title: e.target.value })}
                data-testid="hangar-field-title"
              />
            </label>
            <label className="field">
              <span>Summary</span>
              <textarea
                className="hangar-input short"
                value={form.summary}
                onChange={(e) => change({ summary: e.target.value })}
                placeholder={
                  draft.kind === "scenario"
                    ? "What this demo shows, in a sentence"
                    : "What this kind of work is for, in a sentence"
                }
                data-testid="hangar-field-summary"
              />
            </label>
            {draft.kind === "scenario" ? (
              <>
                <label className="field">
                  <span>Runs the workflow</span>
                  <select
                    className="hangar-input"
                    value={form.workflow}
                    onChange={(e) => change({ workflow: e.target.value })}
                    data-testid="hangar-field-workflow"
                  >
                    {hangar.workflows.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Opening line</span>
                  <input
                    className="hangar-input"
                    value={form.opening}
                    onChange={(e) => change({ opening: e.target.value })}
                    placeholder="What the person says first, e.g. Let's review the Allowances PRD."
                    data-testid="hangar-field-opening"
                  />
                </label>
              </>
            ) : (
              <StepsField value={form.steps} onChange={(steps) => change({ steps })} />
            )}
          </section>
          <section className="card editing">
            <span className="lab">
              {draft.kind === "scenario" ? "Cast · who takes part" : "Who may be called"}
            </span>
            <div className="castpick single">
              <fieldset>
                {hangar.people.map((p) => {
                  const on = form.participants.includes(p.id);
                  const outside =
                    draft.kind === "scenario" &&
                    on &&
                    workflow !== undefined &&
                    workflow.participants.length > 0 &&
                    !workflow.participants.includes(p.id);
                  return (
                    <label key={p.id}>
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={() =>
                          change({
                            participants: on
                              ? form.participants.filter((i) => i !== p.id)
                              : [...form.participants, p.id],
                          })
                        }
                      />
                      <span>
                        {p.name}
                        <span className="lab"> · {p.role || p.kind}</span>
                        {outside && <span className="chip fail"> not called by the workflow</span>}
                      </span>
                    </label>
                  );
                })}
              </fieldset>
            </div>
          </section>
          <section className="card editing">
            <div className="row">
              <span className="lab">
                {draft.kind === "scenario"
                  ? `Script · ${mainFile}`
                  : "Instructions · SKILL.md (what the agent does)"}
              </span>
              <span className="sp" />
              {draft.kind === "scenario" && (
                <span className="lab">
                  **Name:** speaks · [show view] · [wait] · [live] under a line: a real agent
                  answers it when flown
                </span>
              )}
            </div>
            <textarea
              className="hangar-input brief tall"
              value={fileText(mainFile)}
              onChange={(e) => setFile(mainFile, e.target.value)}
              spellCheck={false}
              aria-label={mainFile}
              data-testid="hangar-field-main"
            />
          </section>
          <FilesCard
            kind={draft.kind}
            files={others}
            openFile={openFile}
            onOpen={setOpenFile}
            text={fileText}
            onChange={setFile}
          />
        </div>
        <div className="flex flex-col gap-3.5">
          <Section title="Checks">
            <Checks problems={draft.problems} passed="Every check passes, and it plays through." />
          </Section>
          <Section title={isNew ? "The new files" : "What changes"}>
            {changed.length === 0 ? (
              <p className="lab">No changes yet.</p>
            ) : (
              <ul className="plain" data-testid="hangar-file-changes">
                {changed.map((f) => (
                  <li key={f.path}>
                    <FileChange file={f} />
                  </li>
                ))}
              </ul>
            )}
            <span className="path">
              {draft.path} → {draft.target}
            </span>
          </Section>
          {draft.kind === "workflow" && (
            <Section title="Used by">
              <Links
                items={[
                  ...draft.uses.scenarios.map((s) => ({
                    to: hangarPath.scenario(s),
                    label: hangar.scenarios.find((x) => x.id === s)?.title ?? s,
                    note: "scenario",
                  })),
                  ...draft.uses.starters.map((s) => ({
                    to: hangarPath.starter(s),
                    label: hangar.starters.find((x) => x.id === s)?.title ?? s,
                    note: "starter",
                  })),
                ]}
                empty="Nothing uses it yet."
              />
            </Section>
          )}
        </div>
      </div>
      {draft.kind === "workflow" && (
        <WidgetsCard
          workflowId={draft.id}
          version={draft.updated}
          views={draft.views ?? []}
          manifestViews={form.views}
          text={fileText}
          onFile={setFile}
          onViews={(views) => change({ views })}
          focus={focus}
        />
      )}
      {draft.kind === "scenario" && (
        <Section title="Play it" aside={<span className="lab">the draft, as a demo</span>}>
          {draft.problems.length === 0 ? (
            <Rendered
              path={`${folderPreviewPath("scenario", draft.id)}?v=${encodeURIComponent(draft.updated ?? "")}`}
              title={`${title}: preview`}
              height={720}
            />
          ) : (
            <p className="lab">It plays once every check passes.</p>
          )}
        </Section>
      )}
      <div className="pubbar">
        <span className="chip build">Draft</span>
        <input
          className="hangar-input"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="One line on what changed (kept in History)"
          aria-label="What changed"
        />
        <button
          type="button"
          className="hangar-btn pri"
          disabled={blocked || publish.isPending}
          title={draft.problems.length > 0 ? "Fix every check first" : undefined}
          data-testid="hangar-publish"
          onClick={() =>
            publish.mutate(
              {
                kind: draft.kind,
                id: draft.id,
                summary: summary || (isNew ? `added ${title}` : ""),
              },
              { onSuccess: () => navigate(livePath(draft.kind, draft.id)) },
            )
          }
        >
          Publish
        </button>
        <button
          type="button"
          className="hangar-btn quiet"
          disabled={discard.isPending}
          onClick={() =>
            discard.mutate(
              { kind: draft.kind, id: draft.id },
              {
                onSuccess: () =>
                  navigate(
                    isNew ? hangarPath.shelf(SHELF[draft.kind]) : livePath(draft.kind, draft.id),
                  ),
              },
            )
          }
        >
          Discard draft
        </button>
        <ActionError error={publish.error ?? discard.error ?? edit.error} />
      </div>
      <AviatorPopover
        name={title}
        workspace={hangar.workspace_dir}
        pinned={pinned}
        onPinnedChange={setPinned}
        sessionId={draft.aviator}
        onSession={(aviator) => editMutate({ kind: draft.kind, id: draft.id, edit: { aviator } })}
        firstPrompt={folderAviatorPrompt(draft, title)}
        intro={
          draft.kind === "scenario"
            ? "Aviator can write or rework the script, invent fixture data, or add a person to the cast. Its changes land in this draft and show on the page as it works."
            : "Aviator can rewrite the instructions, add a step or a view, or change who may be called. Its changes land in this draft and show on the page as it works."
        }
        trial={
          draft.kind === "scenario"
            ? {
                tab: "Play it",
                intro:
                  "Aviator plays the draft the way someone flying would meet it, from the start or from a point you name. Nothing is published.",
                placeholder: "Where to start, or what to watch (optional)",
                prompt: (note) => playPrompt(draft.id, note),
              }
            : undefined
        }
      />
    </div>
  );
}

function StepsField({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="field">
      <span>Steps (2 to 8, as the person would say them)</span>
      <ol className="stepsedit">
        {value.map((step, i) => (
          // oxlint-disable-next-line react/no-array-index-key -- steps are edited in place by position
          <li key={i} className="row">
            <input
              className="hangar-input"
              value={step}
              onChange={(e) => onChange(value.map((s, j) => (j === i ? e.target.value : s)))}
              aria-label={`Step ${i + 1}`}
            />
            <button
              type="button"
              className="del"
              aria-label={`Remove step ${i + 1}`}
              onClick={() => onChange(value.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </li>
        ))}
      </ol>
      <button type="button" className="addtag" onClick={() => onChange([...value, ""])}>
        + Add a step
      </button>
    </div>
  );
}

const FOLDER_HINT = {
  scenario: "context/brief.md, cast/mara-okafor.md or fixtures/notes.md",
  workflow: "references/brief.md or schemas/records.json",
};

function FilesCard({
  kind,
  files,
  openFile,
  onOpen,
  text,
  onChange,
}: {
  kind: FolderKind;
  files: FolderFile[];
  openFile: string | null;
  onOpen: (path: string | null) => void;
  text: (path: string) => string;
  onChange: (path: string, text: string | null) => void;
}) {
  const [adding, setAdding] = useState("");
  return (
    <section className="card editing">
      <span className="lab">
        {kind === "scenario"
          ? "Files · invented data, context and story notes"
          : "Other files · schemas and references"}
      </span>
      <ul className="files" data-testid="hangar-files">
        {files
          .filter((f) => f.change !== "removed")
          .map((f) => (
            <li key={f.path}>
              <div className="row">
                <button
                  type="button"
                  className={cn("filename", openFile === f.path && "on")}
                  onClick={() => onOpen(openFile === f.path ? null : f.path)}
                  disabled={!f.editable}
                  title={f.editable ? "Edit" : "Not a text file this page can edit"}
                >
                  {f.path}
                </button>
                {f.change !== "same" && <span className="chip build">{f.change}</span>}
                <span className="sp" />
                <button
                  type="button"
                  className="del"
                  aria-label={`Delete ${f.path}`}
                  onClick={() => onChange(f.path, null)}
                >
                  ×
                </button>
              </div>
              {openFile === f.path && (
                <textarea
                  className="hangar-input brief"
                  value={text(f.path)}
                  onChange={(e) => onChange(f.path, e.target.value)}
                  spellCheck={false}
                  aria-label={f.path}
                />
              )}
            </li>
          ))}
      </ul>
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          const path = adding.trim();
          if (!path) return;
          onChange(path, path.endsWith(".json") ? "{}\n" : "");
          onOpen(path);
          setAdding("");
        }}
      >
        <input
          className="hangar-input"
          value={adding}
          onChange={(e) => setAdding(e.target.value)}
          placeholder={`Add a file, e.g. ${FOLDER_HINT[kind]}`}
          aria-label="New file path"
        />
        <button type="submit" className="hangar-btn" disabled={!adding.trim()}>
          Add
        </button>
      </form>
    </section>
  );
}

function FileChange({ file }: { file: FolderFile }) {
  const [open, setOpen] = useState(false);
  const sign = file.change === "added" ? "+" : file.change === "removed" ? "−" : "~";
  return (
    <>
      <button type="button" className="linkish" onClick={() => setOpen(!open)}>
        <span className={file.change === "removed" ? "del" : "add"}>{sign}</span> {file.path}
        <span className="lab"> · {file.change}</span>
      </button>
      {open &&
        (file.text != null || file.live != null ? (
          <Diff before={file.live ?? ""} after={file.text ?? ""} />
        ) : (
          <p className="lab">Not a text file.</p>
        ))}
    </>
  );
}

/** "Edit", "Duplicate" and "Remove" for a scenario or workflow page. */
export function FolderActions({
  hangar,
  kind,
  id,
  builtin,
  shipped,
}: {
  hangar: Hangar;
  kind: FolderKind;
  id: string;
  builtin: boolean;
  shipped?: boolean;
}) {
  const navigate = useNavigate();
  const { startDraft, create } = useFolderActions();
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  const existing = hangar.folder_drafts.find((d) => d.kind === kind && d.id === id);
  if (existing) {
    return (
      <Link className="hangar-btn pri" to={hangarPath.folderDraft(kind, id)}>
        Open the draft
      </Link>
    );
  }
  const open = (d: FolderDraft) => navigate(hangarPath.folderDraft(d.kind, d.id));
  return (
    <div className="row">
      <button
        type="button"
        className="hangar-btn pri"
        disabled={startDraft.isPending}
        onClick={() => startDraft.mutate({ kind, id }, { onSuccess: open })}
        data-testid="hangar-edit"
        title={builtin ? "Ships with the app: editing makes a workspace copy" : undefined}
      >
        {builtin ? "Edit a copy" : "Edit"}
      </button>
      {naming ? (
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim())
              create.mutate({ kind, name: name.trim(), duplicateOf: id }, { onSuccess: open });
          }}
        >
          <input
            className="hangar-input"
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name of the copy"
            aria-label="Name of the copy"
          />
          <button type="submit" className="hangar-btn" disabled={!name.trim()}>
            Create draft
          </button>
        </form>
      ) : (
        <button type="button" className="hangar-btn" onClick={() => setNaming(true)}>
          Duplicate
        </button>
      )}
      {!builtin && (
        <button
          type="button"
          className="hangar-btn quiet"
          onClick={() => startDraft.mutate({ kind, id, remove: true }, { onSuccess: open })}
        >
          {shipped ? "Go back to the shipped one" : "Remove"}
        </button>
      )}
      <ActionError error={startDraft.error ?? create.error} />
    </div>
  );
}

/** "New scenario": a name and the workflow it runs. */
export function NewScenarioButton({ hangar }: { hangar: Hangar }) {
  const navigate = useNavigate();
  const { create } = useFolderActions();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [workflow, setWorkflow] = useState(hangar.workflows[0]?.id ?? "");
  if (!open) {
    return (
      <button
        type="button"
        className="hangar-btn pri"
        onClick={() => setOpen(true)}
        data-testid="hangar-new-scenario"
      >
        New scenario
      </button>
    );
  }
  return (
    <form
      className="row"
      onSubmit={(e) => {
        e.preventDefault();
        if (!name.trim()) return;
        create.mutate(
          { kind: "scenario", name: name.trim(), workflow },
          { onSuccess: (d) => navigate(hangarPath.folderDraft("scenario", d.id)) },
        );
      }}
    >
      <input
        className="hangar-input"
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Its name, e.g. Card freeze demo"
        aria-label="Name"
      />
      <select
        className="hangar-input"
        value={workflow}
        onChange={(e) => setWorkflow(e.target.value)}
        aria-label="Workflow it runs"
      >
        {hangar.workflows.map((w) => (
          <option key={w.id} value={w.id}>
            {w.title}
          </option>
        ))}
      </select>
      <button type="submit" className="hangar-btn pri" disabled={!name.trim() || create.isPending}>
        Create draft
      </button>
      <button type="button" className="hangar-btn quiet" onClick={() => setOpen(false)}>
        Cancel
      </button>
      <ActionError error={create.error} />
    </form>
  );
}

/** Earlier versions kept by Publish, each one a way back through the same gate. */
export function FolderHistory({
  kind,
  id,
  versions,
}: {
  kind: FolderKind;
  id: string;
  versions: FolderVersion[];
}) {
  const { restore } = useFolderActions();
  if (versions.length === 0) return null;
  return (
    <details className="card" data-testid="hangar-folder-history">
      <summary className="lab">History · {versions.length}</summary>
      <ul className="plain">
        {versions.map((v) => (
          <li key={v.version} className="row">
            <span>{v.summary || "published"}</span>
            <span className="lab">{v.at ? new Date(v.at).toLocaleString() : v.version}</span>
            <span className="sp" />
            <button
              type="button"
              className="hangar-btn quiet"
              disabled={restore.isPending}
              onClick={() => restore.mutate({ kind, id, version: v.version })}
            >
              Restore
            </button>
          </li>
        ))}
      </ul>
      <ActionError error={restore.error} />
    </details>
  );
}

/** "Edit" beside a workflow's widgets, or one widget: opens the workflow's draft there (D-112). */
export function EditWidgetButton({
  hangar,
  workflow,
  view,
  builtin,
  label,
}: {
  hangar: Hangar;
  workflow: string;
  view?: string;
  builtin: boolean;
  label?: string;
}) {
  const navigate = useNavigate();
  const { startDraft } = useFolderActions();
  const where = `${hangarPath.folderDraft("workflow", workflow)}${view ? `#widget-${encodeURIComponent(view)}` : "#widgets"}`;
  const text = label ?? (view ? "Edit this one" : "Edit widgets and views");
  if (hangar.folder_drafts.some((d) => d.kind === "workflow" && d.id === workflow)) {
    return (
      <Link className="hangar-btn" to={where} data-testid="hangar-edit-widget">
        {text}
      </Link>
    );
  }
  return (
    <button
      type="button"
      className="hangar-btn"
      disabled={startDraft.isPending}
      title={
        builtin ? "Ships with the app: editing makes a workspace copy of the workflow" : undefined
      }
      onClick={() =>
        startDraft.mutate({ kind: "workflow", id: workflow }, { onSuccess: () => navigate(where) })
      }
      data-testid="hangar-edit-widget"
    >
      {text}
    </button>
  );
}
