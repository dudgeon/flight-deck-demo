/**
 * omnigent-slim Library page (``/library``): where work and demos start (D-82 to D-88).
 *
 * Nothing here is typed into the Library. The top half is the featured product
 * skills, read from each workflow's ``library`` block in ``workflow.json``: one
 * spotlight, then a grid in rough product-lifecycle order. The lower half is the
 * published scenarios, each flown as a demo with the same route and button as
 * the Hangar's "Fly this". See ``omnigent/server/routes/slim_library.py``.
 *
 * Starting a skill never sends anything by itself: it opens the new-session
 * composer with the prompt filled in (``/?prompt=``), and the person presses Send.
 */

import { useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useNavigate } from "@/lib/routing";
import { FlyButton } from "@/hangar/FlyButton";
import { HANGAR_WRENCH_GROUP, HangarWrench } from "@/hangar/HangarWrench";
import { type DemoInfo, hangarPath } from "@/hangar/hangarApi";
import { authenticatedFetch } from "@/lib/identity";
import { cn } from "@/lib/utils";
import "./library.css";

interface Field {
  name: string;
  hint: string;
}

interface Starter {
  id: string;
  title: string;
  description: string;
  prompt: string;
  fields: Field[];
}

export interface LibrarySkill {
  id: string;
  title: string;
  summary: string;
  steps: string[];
  prompt: string;
  fields: Field[];
  spotlight: boolean;
  starters: Starter[];
  demos: { id: string; title: string }[];
}

interface CastMember {
  id: string;
  name: string;
  initials: string;
  avatar: string | null;
}

export interface LibraryDemo {
  id: string;
  title: string;
  summary: string;
  workflow: string;
  workflow_title: string;
  cast: CastMember[];
  turns: number;
  live_turns: number;
  meter: boolean[];
  kind: "Scripted" | "Mixed";
  length_minutes: number | null;
  demo: DemoInfo | null;
}

export interface Library {
  library_dir: string | null;
  project: string | null;
  skills: LibrarySkill[];
  demos: LibraryDemo[];
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

const label = (name: string) => {
  const text = name.replace(/[-_]/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};

/** The short form a skill's inputs become, and Start. */
function StartForm({
  prompt,
  fields,
  project,
  cta = "Start",
  note,
}: {
  prompt: string;
  fields: Field[];
  project: string | null;
  cta?: string;
  /** Say that Start only opens the composer (once, on the spotlight). */
  note?: boolean;
}) {
  const navigate = useNavigate();
  const id = useId();
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <form
      className="lib-form"
      onSubmit={(event) => {
        event.preventDefault();
        navigate(composerLink(fillPrompt(prompt, values), project));
      }}
    >
      {fields.map((field) => (
        <label key={field.name} htmlFor={`${id}-${field.name}`}>
          <span>{label(field.name)}</span>
          <input
            id={`${id}-${field.name}`}
            className="lib-input"
            placeholder={field.hint}
            value={values[field.name] ?? ""}
            onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
          />
        </label>
      ))}
      <div className="lib-acts">
        <button type="submit" className="lib-btn pri">
          {cta}
        </button>
        {note && (
          <span className="lib-note">Opens the composer. Nothing is sent until you press Send.</span>
        )}
      </div>
    </form>
  );
}

function SkillCard({
  skill,
  project,
  spotlight,
}: {
  skill: LibrarySkill;
  project: string | null;
  spotlight?: boolean;
}) {
  const [starter, setStarter] = useState<Starter | null>(null);
  return (
    <article
      className={cn("lib-card lib-skill", spotlight && "spot", HANGAR_WRENCH_GROUP)}
      data-testid={spotlight ? "library-spotlight" : "library-skill"}
    >
      <div className="lib-head">
        {spotlight && <span className="lib-eyebrow">Start here</span>}
        <h3>{skill.title}</h3>
        <HangarWrench
          to={hangarPath.workflow(skill.id)}
          label={`Open ${skill.title} in the Hangar`}
        />
      </div>
      <p className="lib-sum">{skill.summary}</p>
      <div className={cn("lib-body", spotlight && "split")}>
        {skill.steps.length > 0 && (
          <ul className="lib-steps" aria-label="What it covers">
            {skill.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        )}
        <div className="lib-start">
          {starter ? (
            <>
              <div className="lib-starter-head">
                <b>{starter.title}</b>
                <button type="button" className="lib-link" onClick={() => setStarter(null)}>
                  Back
                </button>
              </div>
              <StartForm
                key={starter.id}
                prompt={starter.prompt}
                fields={starter.fields}
                project={project}
                note={spotlight}
              />
            </>
          ) : (
            <StartForm
              prompt={skill.prompt}
              fields={skill.fields}
              project={project}
              note={spotlight}
            />
          )}
          {skill.starters.length > 0 && !starter && (
            <div className="lib-more">
              Other ways in:{" "}
              {skill.starters.map((s) => (
                <button key={s.id} type="button" className="lib-link" onClick={() => setStarter(s)}>
                  {s.title}
                </button>
              ))}
            </div>
          )}
          {skill.demos.length > 0 && (
            <div className="lib-more">
              See it flown:{" "}
              {skill.demos.map((d) => (
                <a key={d.id} className="lib-link" href={`#demo-${d.id}`}>
                  {d.title}
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

function CastMarks({ cast }: { cast: CastMember[] }) {
  if (cast.length === 0) return null;
  return (
    <span className="lib-marks" aria-label={`With ${cast.map((c) => c.name).join(", ")}`}>
      {cast.map((c) => (
        <span key={c.id} className="lib-mark" title={c.name}>
          {c.avatar ? <img src={c.avatar} alt="" /> : c.initials}
        </span>
      ))}
    </span>
  );
}

function progress(demo: DemoInfo): string {
  if (demo.finished) return "played to the end";
  return demo.turn ? `turn ${demo.turn} of ${demo.turns}` : "not started yet";
}

function DemoCard({ demo }: { demo: LibraryDemo }) {
  const switchId = useId();
  const [live, setLive] = useState(demo.demo?.live_turns ?? true);
  const hasLive = demo.live_turns > 0;
  return (
    <article
      id={`demo-${demo.id}`}
      className={cn("lib-card lib-demo", HANGAR_WRENCH_GROUP)}
      data-testid="library-demo"
    >
      <div className="lib-head">
        <span className="lib-kind">◆ Demo · {demo.kind}</span>
        <HangarWrench
          to={hangarPath.scenario(demo.id)}
          label={`Open ${demo.title} in the Hangar`}
        />
      </div>
      <h3>{demo.title}</h3>
      <p className="lib-sum">{demo.summary}</p>
      <div className="lib-meta">
        <span className="lib-chip">{demo.workflow_title}</span>
        <CastMarks cast={demo.cast} />
      </div>
      <div className="lib-meta">
        <span className="lib-meter" aria-hidden="true">
          {demo.meter.map((on, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: one tick per turn, in order
            <i key={i} className={on && live ? "live" : undefined} />
          ))}
        </span>
        <span>
          {hasLive
            ? live
              ? `${demo.live_turns} of ${demo.turns} turns live`
              : `${demo.turns} turns, all canned`
            : `${demo.turns} turns, fully scripted`}
          {demo.length_minutes ? ` · about ${demo.length_minutes} min` : ""}
        </span>
      </div>
      <div className="lib-fly">
        <FlyButton scenarioId={demo.id} demo={demo.demo} label="Fly" liveTurns={live} />
        {hasLive && (
          <label className="lib-switch" htmlFor={switchId}>
            <input
              id={switchId}
              type="checkbox"
              role="switch"
              checked={live}
              onChange={(e) => setLive(e.target.checked)}
            />
            Live turns
          </label>
        )}
      </div>
    </article>
  );
}

function InFlight({ demos }: { demos: LibraryDemo[] }) {
  const flown = demos.filter((d) => d.demo && !d.demo.finished);
  if (flown.length === 0) return null;
  return (
    <div className="lib-inflight" data-testid="library-in-flight">
      <h3>In flight</h3>
      {flown.map((d) => (
        <div key={d.id} className="lib-flight">
          <span className="lib-diamond" aria-hidden="true">
            ◆
          </span>
          <div className="lib-flight-text">
            <b>{d.title}</b>
            <span>
              {d.workflow_title} · {d.demo ? progress(d.demo) : ""}
            </span>
          </div>
          <FlyButton scenarioId={d.id} demo={d.demo} label="Continue" />
        </div>
      ))}
    </div>
  );
}

export function LibraryView({ data }: { data: Library }) {
  const spotlight = data.skills.find((s) => s.spotlight);
  const others = data.skills.filter((s) => s !== spotlight);
  return (
    <>
      <section className="lib-section" aria-labelledby="lib-work">
        <h2 id="lib-work">
          Start with a skill <small>on your own material</small>
        </h2>
        {data.skills.length === 0 ? (
          <p className="lib-empty">
            No featured skills yet. A workflow shows here when its workflow.json has{" "}
            <code>"library": {"{"}"show": true{"}"}</code>.
          </p>
        ) : (
          <>
            {spotlight && <SkillCard skill={spotlight} project={data.project} spotlight />}
            {others.length > 0 && (
              <div className="lib-grid">
                {others.map((skill) => (
                  <SkillCard key={skill.id} skill={skill} project={data.project} />
                ))}
              </div>
            )}
          </>
        )}
      </section>
      <section className="lib-section lib-lower" aria-labelledby="lib-demos">
        <h2 id="lib-demos">
          Scenarios and demos <small>invented stories, safe to show</small>
        </h2>
        <InFlight demos={data.demos} />
        {data.demos.length === 0 ? (
          <p className="lib-empty">
            No scenarios yet. Build one in the Hangar and publish it to fly it here.
          </p>
        ) : (
          <div className="lib-grid">
            {data.demos.map((demo) => (
              <DemoCard key={demo.id} demo={demo} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}

export function LibraryPage() {
  const { data, error, isPending } = useQuery({
    queryKey: ["slim-library"],
    queryFn: fetchLibrary,
  });
  return (
    <div className="pa-library">
      <div className="lib-wrap">
        <header>
          <h1>Library</h1>
          <p className="lib-sum">
            Start real work on your own material, or fly a demo of how the work goes.
          </p>
        </header>
        {isPending && <p className="lib-empty">Loading…</p>}
        {error && <p className="lib-error">{String(error)}</p>}
        {data && <LibraryView data={data} />}
      </div>
    </div>
  );
}
