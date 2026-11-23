/**
 * omnigent-slim Library page (``/library``): where work and demos start (D-82 to D-88).
 *
 * Nothing here is typed into the Library. The top half is the arcs (D-153), read
 * from each workflow's ``library`` block in ``workflow.json`` and shown the way the
 * Hangar shows a workflow: its main view drawn from sample data, its steps as
 * chevrons, who it can call in. One spotlight, then a grid in lifecycle order,
 * each tagged with its stage. The lower half is a board of the published scenarios, one row each,
 * flown as a demo with the same route and button as the Hangar's "Fly this"
 * (D-170). See ``omnigent/server/routes/slim_library.py``.
 *
 * Starting a skill never sends anything by itself: it opens the new-session
 * composer with the prompt filled in (``/?prompt=``), and the person presses Send.
 */

import { useQuery } from "@tanstack/react-query";
import { type CSSProperties, useId, useMemo, useState } from "react";
import { useResolvedThemeMode } from "@/components/theme/useResolvedThemeMode";
import { useNavigate } from "@/lib/routing";
import { FlyButton } from "@/hangar/FlyButton";
import { HANGAR_WRENCH_GROUP, HangarWrench } from "@/hangar/HangarWrench";
import { type DemoInfo, hangarPath, useHangarPage, viewPagePath } from "@/hangar/hangarApi";
import { injectDesignTokens } from "@/lib/artifactBridge";
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

/** The view a workflow makes, drawn as the Hangar draws it. */
export interface LibraryViewRef {
  workflow: string;
  name: string;
  title: string;
}

export interface LibrarySkill {
  id: string;
  title: string;
  summary: string;
  steps: string[];
  prompt: string;
  fields: Field[];
  spotlight: boolean;
  /** Lifecycle stage title (Discover, Shape, Requirements, Engage, Deliver). */
  stage?: string | null;
  /** Its main view, drawn from sample data; null when it makes no view. */
  view?: LibraryViewRef | null;
  /** Who it can call in, from the workflow and its parts. */
  cast?: CastMember[];
  starters: Starter[];
  demos: { id: string; title: string }[];
}

interface CastMember {
  id: string;
  name: string;
  initials: string;
  avatar: string | null;
  /** 1 to 8: the person's author colour, the same on every card. */
  hue?: number;
}

export interface LibraryDemo {
  id: string;
  title: string;
  summary: string;
  workflow: string;
  workflow_title: string;
  /** The Library card this demo belongs to: the arc, for a part of one. */
  arc_title?: string;
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
            title={field.hint}
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

/** The steps, drawn as the Hangar draws them: one chevron each, in order. */
function Steps({ steps }: { steps: string[] }) {
  return (
    <ol className="lib-steps" aria-label="Steps">
      {steps.map((step) => (
        <li key={step}>{step}</li>
      ))}
    </ol>
  );
}

/**
 * What the work makes: the workflow's main view, drawn from its scenario's
 * sample data by the same route the Hangar's view thumbnails use (D-170).
 */
function Preview({ view, large }: { view: LibraryViewRef; large?: boolean }) {
  const { data } = useHangarPage(viewPagePath(view));
  const mode = useResolvedThemeMode() === "dark" ? "dark" : "light";
  const srcDoc = useMemo(() => (data ? injectDesignTokens(data, mode) : null), [data, mode]);
  return (
    <figure className={cn("lib-preview", large && "large")}>
      <div className="lib-frame" aria-hidden="true">
        {srcDoc && (
          <iframe
            title={view.title}
            srcDoc={srcDoc}
            // Scripts only: the page cannot reach the app, its storage or the network.
            sandbox="allow-scripts"
            loading="lazy"
            tabIndex={-1}
          />
        )}
      </div>
      <figcaption>
        You get: <b>{view.title}</b>
      </figcaption>
    </figure>
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
      {skill.view ? <Preview view={skill.view} large={spotlight} /> : <div />}
      <div className="lib-head">
        {skill.stage && <span className="lib-stage">{skill.stage}</span>}
        {spotlight && <span className="lib-here">Start here</span>}
        <span className="lib-grow" />
        <HangarWrench
          to={hangarPath.workflow(skill.id)}
          label={`Open ${skill.title} in the Hangar`}
        />
      </div>
      <h3>{skill.title}</h3>
      <p className="lib-sum">{skill.summary}</p>
      {skill.steps.length > 0 ? <Steps steps={skill.steps} /> : <div />}
      <div className="lib-crew">
        {(skill.cast ?? []).length > 0 ? (
          <>
            <CastMarks cast={skill.cast ?? []} />
            <span>Can call in {(skill.cast ?? []).map((c) => c.name).join(", ")}</span>
          </>
        ) : (
          <span>Aviator works with you alone</span>
        )}
      </div>
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
          <StartForm prompt={skill.prompt} fields={skill.fields} project={project} note={spotlight} />
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
            <span className="lib-diamond" aria-hidden="true">
              ◆
            </span>{" "}
            See it flown:{" "}
            {skill.demos.map((d) => (
              <a key={d.id} className="lib-link" href={`#demo-${d.id}`}>
                {d.title}
              </a>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

function CastMarks({ cast }: { cast: CastMember[] }) {
  if (cast.length === 0) return null;
  return (
    <span className="lib-marks" aria-label={`With ${cast.map((c) => c.name).join(", ")}`}>
      {cast.map((c) => (
        <span
          key={c.id}
          className="lib-mark"
          title={c.name}
          style={{ "--lib-hue": `var(--pa-author-${c.hue ?? 1})` } as CSSProperties}
        >
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

/** One row of the demo board: the story, its skill and cast, its turns, and Fly. */
function DemoRow({ demo }: { demo: LibraryDemo }) {
  const switchId = useId();
  const [live, setLive] = useState(demo.demo?.live_turns ?? true);
  const hasLive = demo.live_turns > 0;
  const liveNow = hasLive && live;
  return (
    <li
      id={`demo-${demo.id}`}
      className={cn("lib-demo", HANGAR_WRENCH_GROUP)}
      data-testid="library-demo"
    >
      <div className="lib-demo-story">
        <div className="lib-demo-title">
          <span className="lib-diamond" aria-hidden="true">
            ◆
          </span>
          <h3>{demo.title}</h3>
          <HangarWrench
            to={hangarPath.scenario(demo.id)}
            label={`Open ${demo.title} in the Hangar`}
          />
        </div>
        <p className="lib-sum">{demo.summary}</p>
      </div>
      <div className="lib-demo-who">
        <span className="lib-chip">{demo.arc_title ?? demo.workflow_title}</span>
        <CastMarks cast={demo.cast} />
      </div>
      <div className="lib-demo-turns">
        <span className="lib-meter" aria-hidden="true">
          {demo.meter.map((on, i) => (
            // oxlint-disable-next-line react/no-array-index-key -- one tick per turn, in order
            <i key={i} className={on && liveNow ? "live" : undefined} />
          ))}
        </span>
        <span className="lib-nums">
          {demo.turns} turns
          {demo.length_minutes ? ` · ${demo.length_minutes} min` : ""}
        </span>
        <span className="lib-howlive">
          {liveNow ? `${demo.live_turns} live, the rest scripted` : "Fully scripted"}
        </span>
      </div>
      <div className="lib-demo-fly">
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
    </li>
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
              {d.arc_title ?? d.workflow_title} · {d.demo ? progress(d.demo) : ""}
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
        <div className="lib-section-head">
          <h2 id="lib-work">Start your own work</h2>
          <p>Pick a kind of work and point it at your own material. You make every choice.</p>
        </div>
        {data.skills.length === 0 ? (
          <p className="lib-empty">
            No skills to start yet. A workflow shows here when its workflow.json has{" "}
            <code>"library": {"{"}"show": true{"}"}</code>.
          </p>
        ) : (
          <>
            {spotlight && <SkillCard skill={spotlight} project={data.project} spotlight />}
            {others.length > 0 && (
              <div className="lib-grid lib-skills" data-count={others.length}>
                {others.map((skill) => (
                  <SkillCard key={skill.id} skill={skill} project={data.project} />
                ))}
              </div>
            )}
          </>
        )}
      </section>
      <section className="lib-section" aria-labelledby="lib-demos">
        <div className="lib-section-head">
          <h2 id="lib-demos">Fly a demo</h2>
          <p>Invented stories at an invented company, safe to show. Each one opens its own demo project.</p>
        </div>
        <InFlight demos={data.demos} />
        {data.demos.length === 0 ? (
          <p className="lib-empty">
            No scenarios yet. Build one in the Hangar and publish it to fly it here.
          </p>
        ) : (
          <ul className="lib-board" aria-label="Demos">
            {data.demos.map((demo) => (
              <DemoRow key={demo.id} demo={demo} />
            ))}
          </ul>
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
            Start real work on your own material, or fly a demo to see how the work goes.
          </p>
        </header>
        {isPending && <p className="lib-empty">Loading…</p>}
        {error && <p className="lib-error">{String(error)}</p>}
        {data && <LibraryView data={data} />}
      </div>
    </div>
  );
}
