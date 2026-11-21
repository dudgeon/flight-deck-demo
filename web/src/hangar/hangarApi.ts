/**
 * omnigent-slim: the Hangar catalog (builder mode, slice 1: look only).
 *
 * Everything comes from ``GET /v1/slim/hangar`` (see
 * ``omnigent/server/routes/slim_hangar.py``), which reads the roster, the
 * workflow folders, the Library and the frameworks on every request. Views,
 * templates and scenario players come back as whole HTML pages that the Hangar
 * draws in sandboxed frames.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/identity";

export interface HangarPerson {
  id: string;
  name: string;
  kind: "agent" | "person";
  role: string;
  initials: string;
  stand_in: boolean;
  backing: "session" | "script";
  call_for: string;
  skills: string[] | null;
  /** The picture's URL, when they have one (D-74). */
  avatar?: string | null;
  brief: string;
  path: string;
  problems: string[];
  used_in: { workflows: string[]; starters: string[]; scenarios?: string[] };
  sample: { text: string; scenario: string } | null;
  history: HangarVersion[];
  /** The live file, word for word. */
  text: string;
}

/** An earlier version of a person, kept by Publish (newest first). */
export interface HangarVersion {
  version: string;
  at: string;
  summary: string;
}

/** A person being built. Nobody flying sees it until it is published. */
export interface HangarDraft {
  kind: "person";
  id: string;
  action: "new" | "change" | "remove";
  from: string | null;
  started: string | null;
  updated: string | null;
  step: string | null;
  person: Omit<
    HangarPerson,
    "brief" | "problems" | "used_in" | "sample" | "history" | "path"
  > | null;
  brief: string;
  text: string | null;
  live: string | null;
  problems: string[];
  uses: { workflows: string[]; starters: string[]; scenarios: string[] };
  /** Where they will be called once published. */
  cast: CastSet;
  cast_changes: { kind: CastKind; id: string; change: "add" | "remove" }[];
  /** The Aviator session helping with this draft, if one was started. */
  aviator: string | null;
  /** The draft picks a different picture (or none) from the live one. */
  avatar_changed?: boolean;
  path: string;
  target: string;
}

export type CastKind = "workflows" | "scenarios" | "starters";
export type CastSet = Record<CastKind, string[]>;

/** What the page edits directly; saved into the draft as you type. */
export interface PersonEdit {
  fields?: Partial<
    Pick<HangarPerson, "name" | "kind" | "role" | "backing" | "call_for"> & { skills: string[] }
  >;
  brief?: string;
  cast?: Partial<CastSet>;
  aviator?: string;
}

export interface HangarView {
  key: string;
  name: string;
  workflow: string;
  title: string;
  heading: string;
  layout: string;
  host: "canvas" | "chat";
  actions: number;
  path: string;
}

export interface HangarRecordType {
  name: string;
  required: string[];
  fields: { name: string; enum: string[] | null; note: string }[];
}

export interface HangarWorkflow {
  id: string;
  title: string;
  summary: string;
  description: string;
  steps: string[];
  progress: { noun?: string; label?: string } | null;
  inputs: { name: string; kind?: string; hint?: string }[];
  launchers: { label: string; on?: string; prompt?: string }[];
  work_products: { name: string; view?: string; out?: string }[];
  participants: string[];
  records: HangarRecordType[];
  views: HangarView[];
  script: { path: string; title: string; steps: number; error: string | null } | null;
  builtin: boolean;
  /** A workflow of this id ships with the app (a workspace copy may hide it). */
  shipped?: boolean;
  history?: FolderVersion[];
  path: string;
  problems: string[];
  starters: string[];
}

export interface HangarTemplate {
  key: string;
  id: string;
  title: string;
  description: string;
  path: string;
  starters: string[];
}

export interface HangarScenario {
  id: string;
  workflow: string;
  title: string;
  steps: number;
  error: string | null;
  path: string;
  summary?: string;
  script_path?: string;
  text: string;
  cast: string[];
  fixtures: string[];
  opening?: string;
  history?: FolderVersion[];
  problems: string[];
}

export interface FolderVersion {
  version: string;
  at: string;
  summary: string;
  files: string[];
}

export type FolderKind = "scenario" | "workflow";

/** One file of a scenario or workflow draft, beside the live one. */
export interface FolderFile {
  path: string;
  change: "same" | "changed" | "added" | "removed";
  size: number;
  /** Text, for text files (not in the catalog listing; the editor fetches it). */
  text?: string | null;
  live?: string | null;
  editable: boolean;
}

/** A scenario or workflow being built: a copy of the whole folder (D-71). */
export interface FolderDraft {
  kind: FolderKind;
  id: string;
  action: "new" | "change" | "remove";
  from: string | null;
  /** The live one ships with the app; publishing makes a workspace copy. */
  builtin: boolean;
  shipped: boolean;
  started: string | null;
  updated: string | null;
  step: string | null;
  aviator: string | null;
  manifest: Record<string, unknown> & {
    title?: string;
    summary?: string;
    workflow?: string;
    participants?: string[];
    steps?: string[];
    script?: string;
    opening?: string;
  };
  manifest_file: string;
  files: FolderFile[];
  problems: string[];
  uses: { scenarios: string[]; starters: string[] };
  path: string;
  target: string;
}

export interface FolderEdit {
  manifest?: Record<string, unknown>;
  files?: Record<string, string | null>;
  aviator?: string;
}

export interface HangarSkill {
  id: string;
  name: string;
  description: string;
  workflow: boolean;
  files: string[];
  path: string;
  used_by: string[];
}

export interface HangarStarter {
  id: string;
  title: string;
  description: string;
  template: string | null;
  prompt: string;
  fields: { name: string; hint: string }[];
  path: string;
  workflows: string[];
  participants: string[];
}

export interface HangarFramework {
  id: string;
  title: string;
  text: string;
  path: string;
  used_by: string[];
}

export interface Hangar {
  workspace_dir: string;
  skills_dir: string;
  people: HangarPerson[];
  workflows: HangarWorkflow[];
  views: HangarView[];
  templates: HangarTemplate[];
  scenarios: HangarScenario[];
  skills: HangarSkill[];
  starters: HangarStarter[];
  frameworks: HangarFramework[];
  /** Drafts of people. */
  drafts: HangarDraft[];
  /** Drafts of scenarios and workflows. */
  folder_drafts: FolderDraft[];
  /** Published files not yet committed to the repo (D-75). */
  repo?: { git: boolean; uncommitted: string[]; count?: number; sent?: RepoSend | null };
}

/** The last "Send to repo" from this copy (D-113). */
export interface RepoSend {
  branch: string;
  commit: string;
  files: number;
  at: string;
  /** The pull request `gh` opened, when it is installed. */
  pull_request: string | null;
  /** Otherwise, GitHub's page to open one. */
  open_pr: string | null;
  summary: string;
}

/** Commit the published configuration to a new branch and push it (D-113). */
export function useSendToRepo() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (summary: string) =>
      send("/v1/slim/hangar/repo/send", "POST", { summary }) as Promise<RepoSend>,
    onSuccess: () => client.invalidateQueries({ queryKey: ["slim-hangar"] }),
  });
}

async function fetchHangar(): Promise<Hangar> {
  const res = await authenticatedFetch("/v1/slim/hangar");
  if (!res.ok) throw new Error(`The Hangar could not be read (${res.status})`);
  const data = (await res.json()) as Omit<Hangar, "drafts"> & {
    drafts: (HangarDraft | FolderDraft)[];
  };
  return {
    ...data,
    drafts: data.drafts.filter((d): d is HangarDraft => d.kind === "person"),
    folder_drafts: data.drafts.filter((d): d is FolderDraft => d.kind !== "person"),
  };
}

export function useHangar() {
  return useQuery({ queryKey: ["slim-hangar"], queryFn: fetchHangar, staleTime: 5_000 });
}

/** A rendered page: a workflow view, a template or a scenario player. */
export function useHangarPage(path: string | null) {
  return useQuery({
    queryKey: ["slim-hangar-page", path],
    enabled: path !== null,
    staleTime: 30_000,
    queryFn: async () => {
      const res = await authenticatedFetch(path as string);
      if (!res.ok) throw new Error(`Could not draw this (${res.status})`);
      return res.text();
    },
  });
}

export const viewPagePath = (view: Pick<HangarView, "workflow" | "name">) =>
  `/v1/slim/hangar/views/${encodeURIComponent(view.workflow)}/${encodeURIComponent(view.name)}`;
export const templatePagePath = (id: string) =>
  `/v1/slim/hangar/templates/${encodeURIComponent(id)}`;
export const previewPagePath = (workflow: string) =>
  `/v1/slim/hangar/preview/${encodeURIComponent(workflow)}`;

/** The id a participant's name maps to when only the name is known (a chat turn). */
export function participantSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/** Where in the Hangar each thing lives. */
export const hangarPath = {
  home: () => "/hangar",
  shelf: (shelf: string) => `/hangar/${shelf}`,
  person: (id: string) => `/hangar/people/${encodeURIComponent(id)}`,
  workflow: (id: string) => `/hangar/workflows/${encodeURIComponent(id)}`,
  view: (workflow: string, name: string) =>
    `/hangar/views/${encodeURIComponent(workflow)}/${encodeURIComponent(name)}`,
  template: (id: string) => `/hangar/views/template/${encodeURIComponent(id)}`,
  scenario: (id: string) => `/hangar/scenarios/${encodeURIComponent(id)}`,
  skill: (id: string) => `/hangar/skills/${encodeURIComponent(id)}`,
  starter: (id: string) => `/hangar/starters/${encodeURIComponent(id)}`,
  framework: (id: string) => `/hangar/frameworks/${encodeURIComponent(id)}`,
  draft: (id: string) => `/hangar/drafts/person/${encodeURIComponent(id)}`,
  folderDraft: (kind: FolderKind, id: string) => `/hangar/drafts/${kind}/${encodeURIComponent(id)}`,
  history: (id: string) => `/hangar/people/${encodeURIComponent(id)}/history`,
};

// ------------------------------------------------------------------ building

async function send(path: string, method: string, body?: unknown): Promise<unknown> {
  const res = await authenticatedFetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = (await res.json().catch(() => ({}))) as { detail?: string };
  if (!res.ok) throw new Error(data.detail ?? `The Hangar refused (${res.status})`);
  return data;
}

const draftApi = (id: string) => `/v1/slim/hangar/drafts/person/${encodeURIComponent(id)}`;

/** Draft, publish, discard and restore: each refreshes the whole Hangar. */
export function useHangarActions() {
  const client = useQueryClient();
  const done = () => client.invalidateQueries({ queryKey: ["slim-hangar"] });
  return {
    startDraft: useMutation({
      mutationFn: ({ id, remove }: { id: string; remove?: boolean }) =>
        send(draftApi(id), "POST", { remove: Boolean(remove) }),
      onSuccess: done,
    }),
    edit: useMutation({
      mutationFn: ({ id, edit }: { id: string; edit: PersonEdit }) =>
        send(draftApi(id), "PATCH", edit) as Promise<HangarDraft>,
      onSuccess: done,
    }),
    create: useMutation({
      mutationFn: ({ name, duplicateOf }: { name: string; duplicateOf?: string }) =>
        send("/v1/slim/hangar/drafts/person", "POST", {
          name,
          duplicate_of: duplicateOf ?? null,
        }) as Promise<HangarDraft>,
      onSuccess: done,
    }),
    discard: useMutation({
      mutationFn: (id: string) => send(draftApi(id), "DELETE"),
      onSuccess: done,
    }),
    publish: useMutation({
      mutationFn: ({ id, summary }: { id: string; summary: string }) =>
        send(`${draftApi(id)}/publish`, "POST", { summary }),
      onSuccess: done,
    }),
    restore: useMutation({
      mutationFn: ({ id, version }: { id: string; version: string }) =>
        send(
          `/v1/slim/hangar/history/person/${encodeURIComponent(id)}/${encodeURIComponent(version)}/restore`,
          "POST",
        ),
      onSuccess: done,
    }),
  };
}

const folderApi = (kind: FolderKind, id: string) =>
  `/v1/slim/hangar/drafts/${kind}/${encodeURIComponent(id)}`;

/** A scenario or workflow draft with its files' text, kept fresh with the catalog. */
export function useFolderDraft(kind: FolderKind, id: string) {
  return useQuery({
    queryKey: ["slim-hangar", "folder-draft", kind, id],
    queryFn: async () => (await send(folderApi(kind, id), "GET")) as FolderDraft,
  });
}

export const folderPreviewPath = (kind: FolderKind, id: string) => `${folderApi(kind, id)}/preview`;

/** The same moves as people, for scenarios and workflows. */
export function useFolderActions() {
  const client = useQueryClient();
  const done = () => client.invalidateQueries({ queryKey: ["slim-hangar"] });
  return {
    startDraft: useMutation({
      mutationFn: ({ kind, id, remove }: { kind: FolderKind; id: string; remove?: boolean }) =>
        send(folderApi(kind, id), "POST", { remove: Boolean(remove) }) as Promise<FolderDraft>,
      onSuccess: done,
    }),
    create: useMutation({
      mutationFn: ({
        kind,
        name,
        duplicateOf,
        workflow,
      }: {
        kind: FolderKind;
        name: string;
        duplicateOf?: string;
        workflow?: string;
      }) =>
        send(`/v1/slim/hangar/drafts/${kind}`, "POST", {
          name,
          duplicate_of: duplicateOf ?? null,
          workflow: workflow ?? null,
        }) as Promise<FolderDraft>,
      onSuccess: done,
    }),
    edit: useMutation({
      mutationFn: ({ kind, id, edit }: { kind: FolderKind; id: string; edit: FolderEdit }) =>
        send(folderApi(kind, id), "PATCH", edit) as Promise<FolderDraft>,
      onSuccess: (saved) => {
        client.setQueryData(["slim-hangar", "folder-draft", saved.kind, saved.id], saved);
        void client.invalidateQueries({ queryKey: ["slim-hangar"], exact: true });
      },
    }),
    discard: useMutation({
      mutationFn: ({ kind, id }: { kind: FolderKind; id: string }) =>
        send(folderApi(kind, id), "DELETE"),
      onSuccess: done,
    }),
    publish: useMutation({
      mutationFn: ({ kind, id, summary }: { kind: FolderKind; id: string; summary: string }) =>
        send(`${folderApi(kind, id)}/publish`, "POST", { summary }),
      onSuccess: done,
    }),
    restore: useMutation({
      mutationFn: ({ kind, id, version }: { kind: FolderKind; id: string; version: string }) =>
        send(
          `/v1/slim/hangar/history/${kind}/${encodeURIComponent(id)}/${encodeURIComponent(version)}/restore`,
          "POST",
        ),
      onSuccess: done,
    }),
  };
}

/** The first message of the Aviator session beside a scenario or workflow draft. */
export function folderAviatorPrompt(
  draft: Pick<FolderDraft, "kind" | "id">,
  title: string,
): string {
  return [
    `I'm editing the ${draft.kind} "${title}" in the Hangar, with the scenario-builder skill.`,
    `The draft is the folder ${draft.kind === "scenario" ? ".hangar/drafts/scenarios" : ".hangar/drafts/workflows"}/${draft.id}/.`,
    "Change files only inside that draft folder (never the live one), keep each change small,",
    `check it with \`pa draft ${draft.kind} ${draft.id}\`, and tell me in one line what you changed.`,
    "I can see the page and edit there myself. Nothing is published until I press Publish.",
    "Read the draft now and say in two lines what it does. Then wait for me.",
  ].join(" ");
}

/** Play a scenario draft from a given point, in the same Aviator session. */
export function playPrompt(draftId: string, note: string): string {
  return [
    `Play it: run the unpublished scenario draft .hangar/drafts/scenarios/${draftId}/ as a user would meet it,`,
    "reading its script.md and fixtures, with the views drawn as the script says. Nothing is published.",
    `${note ? `Start from or focus on: ${note}` : ""}`,
  ].join(" ");
}

/** A draft's picture, fresh after each change. */
export const draftAvatarUrl = (draft: Pick<HangarDraft, "id" | "updated">) =>
  `/v1/slim/hangar/avatars/${encodeURIComponent(draft.id)}?draft=1&v=${encodeURIComponent(draft.updated ?? "")}`;

/** Pick or clear a draft's picture: the file is copied into the draft, then the repo on publish. */
export function useAvatarActions() {
  const client = useQueryClient();
  const done = () => client.invalidateQueries({ queryKey: ["slim-hangar"] });
  return {
    set: useMutation({
      mutationFn: async ({ id, file }: { id: string; file: File }) => {
        const res = await authenticatedFetch(
          `/v1/slim/hangar/drafts/person/${encodeURIComponent(id)}/avatar`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/octet-stream", "X-Filename": file.name },
            body: file,
          },
        );
        const data = (await res.json().catch(() => ({}))) as { detail?: string };
        if (!res.ok) throw new Error(data.detail ?? `The picture was refused (${res.status})`);
        return data as HangarDraft;
      },
      onSuccess: done,
    }),
    clear: useMutation({
      mutationFn: (id: string) =>
        send(`/v1/slim/hangar/drafts/person/${encodeURIComponent(id)}/avatar`, "DELETE"),
      onSuccess: done,
    }),
  };
}

/** Every participant's picture by id, for the chat's participant turns. */
export function useAvatars() {
  return useQuery({
    queryKey: ["slim-avatars"],
    staleTime: 60_000,
    retry: false,
    queryFn: async () => (await send("/v1/slim/hangar/avatars", "GET")) as Record<string, string>,
  });
}

export function useHangarVersion(id: string, version: string | null) {
  return useQuery({
    queryKey: ["slim-hangar-version", id, version],
    enabled: version !== null,
    queryFn: async () =>
      (await send(
        `/v1/slim/hangar/history/person/${encodeURIComponent(id)}/${version as string}`,
        "GET",
      )) as HangarVersion & { text: string },
  });
}

/** The project guided builds run in (see slim_bootstrap). */
export const HANGAR_PROJECT = "Hangar";

/** A new session in the Hangar project with this prompt in the composer; the user presses Send. */
export function builderSessionLink(prompt: string): string {
  const params = new URLSearchParams({ project: HANGAR_PROJECT, prompt });
  return `/?${params.toString()}`;
}

export const BUILD_STEPS = [
  "Who they are",
  "How they answer",
  "Where they can be called",
  "Try them",
  "Publish",
] as const;

/** The first message of the Aviator session that sits beside a draft in the Hangar. */
export function aviatorPrompt(draft: Pick<HangarDraft, "id" | "action">, name: string): string {
  return [
    `I'm editing ${draft.action === "new" ? "a new person" : name} in the Hangar, with the build-person skill.`,
    `The draft is .hangar/drafts/people/${draft.id}.md. I can see the page and edit fields there myself,`,
    "so keep each change small, make it with `pa draft person` (never edit participants/ yourself),",
    "and tell me in one line what you changed. Nothing is published until I press Publish.",
    "Read the draft now and say in two lines what it says. Then wait for me.",
  ].join(" ");
}

/** A test question for the draft, asked in the same Aviator session. */
export function trialPrompt(draftId: string, name: string, question: string): string {
  return [
    `Try them (step 4 of build-person): call the unpublished draft ${name} in a background session`,
    `with \`pa who ${draftId} --dir .hangar/drafts/people --opening --ask\`, ask them exactly this,`,
    `and show their answer as their participant turn. Nothing is published. The question: ${question}`,
  ].join(" ");
}

export const buildPrompts = {
  create: () =>
    "Build a new person or agent for the roster with the build-person skill. Start with step 1: ask me who they are.",
  edit: (id: string, name: string) =>
    `Change ${name} with the build-person skill. The draft is .hangar/drafts/people/${id}.md: read it, tell me in two lines what it says now, and ask what I want to change.`,
  duplicate: (id: string, name: string) =>
    `Make a new person or agent starting from a copy of ${name} (${id}), with the build-person skill. Ask me for the new name first.`,
  resume: (id: string, step: string | null) =>
    `Carry on building the draft .hangar/drafts/people/${id}.md with the build-person skill${step ? `, from the step "${step}"` : ""}.`,
  trial: (id: string, name: string) =>
    `Trial of the unpublished draft ${name} (.hangar/drafts/people/${id}.md), with the build-person skill, step 4. Nothing is published. My test question for them: `,
};

/**
 * Which lines a draft removes and adds, for "what changes". A plain longest
 * common subsequence over lines: participant files are short.
 */
export function lineDiff(
  before: string,
  after: string,
): { op: "same" | "add" | "del"; text: string }[] {
  const a = before.split("\n");
  const b = after.split("\n");
  const n = a.length;
  const m = b.length;
  const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const out: { op: "same" | "add" | "del"; text: string }[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      out.push({ op: "same", text: a[i] });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      out.push({ op: "del", text: a[i++] });
    } else {
      out.push({ op: "add", text: b[j++] });
    }
  }
  while (i < n) out.push({ op: "del", text: a[i++] });
  while (j < m) out.push({ op: "add", text: b[j++] });
  return out;
}

/**
 * Join the hard-wrapped lines of a markdown file so it reflows in a narrow
 * column. Blank lines, headings, list items, directives (`[...]`), speech
 * (`**Name:**`), tables and fences keep their own line.
 */
export function unwrap(text: string): string {
  const ownLine = /^\s*([-*#>|[]|\d+[.)]\s|\*\*|```|---)/;
  const out: string[] = [];
  for (const line of text.split("\n")) {
    const prev = out.length > 0 ? out[out.length - 1] : "";
    if (prev.trim() && line.trim() && !ownLine.test(line) && !/^\s*(```|---|\|)/.test(prev)) {
      out[out.length - 1] = `${prev.trimEnd()} ${line.trim()}`;
    } else {
      out.push(line);
    }
  }
  return out.join("\n");
}
