/**
 * omnigent-slim: the Hangar catalog (builder mode, slice 1: look only).
 *
 * Everything comes from ``GET /v1/slim/hangar`` (see
 * ``omnigent/server/routes/slim_hangar.py``), which reads the roster, the
 * workflow folders, the Library and the frameworks on every request. Views,
 * templates and scenario players come back as whole HTML pages that the Hangar
 * draws in sandboxed frames.
 */

import { useQuery } from "@tanstack/react-query";
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
  brief: string;
  path: string;
  problems: string[];
  used_in: { workflows: string[]; starters: string[] };
  sample: { text: string; scenario: string } | null;
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
  text: string;
  cast: string[];
  fixtures: string[];
  problems: string[];
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
}

async function fetchHangar(): Promise<Hangar> {
  const res = await authenticatedFetch("/v1/slim/hangar");
  if (!res.ok) throw new Error(`The Hangar could not be read (${res.status})`);
  return (await res.json()) as Hangar;
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
};

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
