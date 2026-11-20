/**
 * omnigent-slim Library page (``/library``): canned sessions and artifact
 * templates, read from the files under the server's library folder
 * (``workspace/templates`` by default; see ``omnigent/server/routes/slim_library.py``).
 *
 * Starting a canned session never sends anything by itself: it opens the
 * new-session composer with the prompt filled in (``/?prompt=``), in the
 * library's project when one is configured, and the user presses Send.
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authenticatedFetch } from "@/lib/identity";

interface CannedSessionField {
  name: string;
  hint: string;
}

interface CannedSession {
  id: string;
  title: string;
  description: string;
  template: string | null;
  prompt: string;
  fields: CannedSessionField[];
}

interface ArtifactTemplate {
  id: string;
  title: string;
  description: string;
  path: string;
}

interface Library {
  library_dir: string | null;
  project: string | null;
  sessions: CannedSession[];
  templates: ArtifactTemplate[];
}

const FIELD_PATTERN = /\{\{\s*([A-Za-z][\w-]*)\s*(?::\s*[^}]*?)?\s*\}\}/g;

async function fetchLibrary(): Promise<Library> {
  const res = await authenticatedFetch("/v1/slim/library");
  if (!res.ok) throw new Error(`Library request failed (${res.status})`);
  return (await res.json()) as Library;
}

/** Replace each `{{field}}` with its value; an empty value keeps the hint visible. */
export function fillPrompt(prompt: string, values: Record<string, string>): string {
  return prompt.replace(FIELD_PATTERN, (match, name: string) => {
    const value = values[name]?.trim();
    return value ? value : match;
  });
}

function composerLink(prompt: string, project: string | null): string {
  const params = new URLSearchParams();
  if (project) params.set("project", project);
  params.set("prompt", prompt);
  return `/?${params.toString()}`;
}

function templatePrompt(template: ArtifactTemplate): string {
  return [
    `Make a new artifact from the "${template.title}" template (${template.path}).`,
    "Copy it into artifacts/, fill it in for: {{topic: what this artifact is about}}",
    "Then open it in the viewer.",
  ].join("\n");
}

function SessionCard({
  session,
  project,
  templates,
}: {
  session: CannedSession;
  project: string | null;
  templates: ArtifactTemplate[];
}) {
  const navigate = useNavigate();
  const [values, setValues] = useState<Record<string, string>>({});
  const template = session.template ? templates.find((t) => t.id === session.template) : undefined;
  const start = () => navigate(composerLink(fillPrompt(session.prompt, values), project));
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-background p-4">
      <div>
        <div className="font-medium text-foreground">{session.title}</div>
        {session.description && (
          <div className="mt-1 text-sm text-muted-foreground">{session.description}</div>
        )}
        {template && (
          <div className="mt-1 text-xs text-muted-foreground">Artifact: {template.title}</div>
        )}
      </div>
      {session.fields.map((field) => (
        <label key={field.name} className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">{field.name.replace(/[-_]/g, " ")}</span>
          <Input
            value={values[field.name] ?? ""}
            placeholder={field.hint}
            onChange={(event) =>
              setValues((current) => ({ ...current, [field.name]: event.target.value }))
            }
            onKeyDown={(event) => {
              if (event.key === "Enter") start();
            }}
          />
        </label>
      ))}
      <div>
        <Button type="button" onClick={start}>
          Open in composer
        </Button>
      </div>
    </div>
  );
}

function TemplateCard({ template, project }: { template: ArtifactTemplate; project: string | null }) {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-background p-4">
      <div className="font-medium text-foreground">{template.title}</div>
      {template.description && (
        <div className="text-sm text-muted-foreground">{template.description}</div>
      )}
      <div className="font-mono text-xs text-muted-foreground">{template.path}</div>
      <div>
        <Button
          type="button"
          variant="outline"
          onClick={() => navigate(composerLink(templatePrompt(template), project))}
        >
          Use template
        </Button>
      </div>
    </div>
  );
}

export function LibraryPage() {
  const { data, error, isPending } = useQuery({
    queryKey: ["slim-library"],
    queryFn: fetchLibrary,
  });
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-8 md:px-8">
        <header>
          <h1 className="text-xl font-semibold text-foreground">Library</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Canned sessions open the composer with their prompt filled in; you review it and
            press Send. Edit the files in{" "}
            <span className="font-mono">{data?.library_dir ?? "workspace/templates"}</span> to
            change what's here.
          </p>
        </header>
        {isPending && <div className="text-sm text-muted-foreground">Loading…</div>}
        {error && <div className="text-sm text-destructive">{String(error)}</div>}
        {data && (
          <>
            <section className="flex flex-col gap-3">
              <h2 className="text-base font-medium text-foreground">Canned sessions</h2>
              {data.sessions.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No canned sessions yet. Add a <span className="font-mono">.md</span> file to{" "}
                  <span className="font-mono">sessions/</span>.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {data.sessions.map((session) => (
                    <SessionCard
                      key={session.id}
                      session={session}
                      project={data.project}
                      templates={data.templates}
                    />
                  ))}
                </div>
              )}
            </section>
            <section className="flex flex-col gap-3">
              <h2 className="text-base font-medium text-foreground">Artifact templates</h2>
              {data.templates.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No templates yet. Add an <span className="font-mono">.html</span> file to{" "}
                  <span className="font-mono">artifacts/</span>.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {data.templates.map((template) => (
                    <TemplateCard key={template.id} template={template} project={data.project} />
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
