/**
 * omnigent-slim: the Hangar, Product Aviator's builder mode (docs/product/hangar.md).
 *
 * Slice 1 (D-45) only looks. The whole frame changes so nobody can mistake the
 * mode (D-40): a band naming it, a paper sidebar with a dashed edge and the
 * shelves in place of sessions, and a drafting grid behind the work. Each shelf
 * draws things the way a user meets them, and each inspect page has two
 * halves: how it looks when flying, and what it is made of, with every "uses"
 * and "used in" as a link. Drafts, checks-as-you-type, trial and publish come in
 * slice 2; nothing here writes a file.
 */

import {
  ArrowLeftIcon,
  BookOpenIcon,
  CompassIcon,
  FileTextIcon,
  LayoutGridIcon,
  LockIcon,
  type LucideIcon,
  PlayIcon,
  RouteIcon,
  SparklesIcon,
  UsersIcon,
  WarehouseIcon,
  WrenchIcon,
} from "lucide-react";
import { type ReactNode, useMemo, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { useResolvedThemeMode } from "@/components/theme/useResolvedThemeMode";
import { ParticipantTurnBlock } from "@/components/chat/ParticipantTurn";
import { injectDesignTokens } from "@/lib/artifactBridge";
import { Link, useLocation, useNavigate, useParams } from "@/lib/routing";
import { cn } from "@/lib/utils";
import {
  type Hangar,
  type HangarPerson,
  type HangarView,
  type HangarWorkflow,
  BUILD_STEPS,
  builderSessionLink,
  buildPrompts,
  type HangarDraft,
  hangarPath,
  lineDiff,
  participantSlug,
  previewPagePath,
  templatePagePath,
  unwrap,
  useHangar,
  useHangarActions,
  useHangarPage,
  useHangarVersion,
  viewPagePath,
} from "./hangarApi";
import "./hangar.css";

// ---------------------------------------------------------------- the frame

const SHELVES: { id: string; label: string; icon: LucideIcon; count: (h: Hangar) => number }[] = [
  { id: "people", label: "People and agents", icon: UsersIcon, count: (h) => h.people.length },
  { id: "workflows", label: "Workflows", icon: RouteIcon, count: (h) => h.workflows.length },
  {
    id: "views",
    label: "Views",
    icon: LayoutGridIcon,
    count: (h) => h.views.length + h.templates.length,
  },
  { id: "scenarios", label: "Scenarios", icon: PlayIcon, count: (h) => h.scenarios.length },
  { id: "skills", label: "Skills", icon: SparklesIcon, count: (h) => h.skills.length },
  { id: "starters", label: "Starters", icon: FileTextIcon, count: (h) => h.starters.length },
  { id: "frameworks", label: "Frameworks", icon: CompassIcon, count: (h) => h.frameworks.length },
];

function HangarSidebar({ hangar }: { hangar: Hangar | undefined }) {
  const { pathname } = useLocation();
  const shelf = /\/hangar\/?([^/]*)/.exec(pathname)?.[1] ?? "";
  return (
    <nav className="hangar-side" aria-label="Hangar shelves" data-testid="hangar-sidebar">
      <div className="hangar-brand">
        <WarehouseIcon aria-hidden="true" className="size-[18px]" />
        Hangar
      </div>
      <Link
        to={hangarPath.home()}
        className="hangar-nav"
        aria-current={shelf === "" ? "page" : undefined}
      >
        <BookOpenIcon aria-hidden="true" />
        Overview
      </Link>
      {SHELVES.map((item) => (
        <Link
          key={item.id}
          to={hangarPath.shelf(item.id)}
          className="hangar-nav"
          aria-current={shelf === item.id ? "page" : undefined}
          data-testid={`hangar-shelf-${item.id}`}
        >
          <item.icon aria-hidden="true" />
          {item.label}
          <span className="n">{hangar ? item.count(hangar) : ""}</span>
        </Link>
      ))}
      <div className="hangar-sidehd">Drafts</div>
      {hangar && hangar.drafts.length === 0 && (
        <p className="hangar-sidenote">Nothing is being built.</p>
      )}
      {hangar?.drafts.map((draft) => (
        <Link
          key={draft.id}
          to={hangarPath.draft(draft.id)}
          className="hangar-nav"
          aria-current={pathname === hangarPath.draft(draft.id) ? "page" : undefined}
          data-testid="hangar-draft-nav"
        >
          <WrenchIcon aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate">{draftName(draft)}</span>
          <span className="n">{draft.problems.length === 0 ? "ready" : draftStepLabel(draft)}</span>
        </Link>
      ))}
      <div className="grow" />
      <div className="hangar-foot">
        <Link to="/" className="hangar-back" data-testid="hangar-back-foot">
          <ArrowLeftIcon aria-hidden="true" className="size-3.5" />
          Back to flying
        </Link>
      </div>
    </nav>
  );
}

export function HangarPage() {
  const { data, error, isPending } = useHangar();
  return (
    <div className="hangar" data-testid="hangar" data-mode="hangar">
      <header className="hangar-band" data-testid="hangar-band">
        <WarehouseIcon aria-hidden="true" className="size-4 shrink-0" />
        Hangar
        <small>
          Where the people, workflows and views others fly are defined. Nothing is live until you
          publish.
        </small>
        <span className="sp" />
        <Link to="/" data-testid="hangar-back-band">
          Back to flying
        </Link>
      </header>
      <HangarSidebar hangar={data} />
      <main className="hangar-main">
        <div className="hangar-pad">
          {isPending && <p className="sub">Reading the hangar…</p>}
          {error && <p className="chip fail">{String(error)}</p>}
          {data && (
            <Routes>
              <Route index element={<Overview hangar={data} />} />
              <Route path="people" element={<PeopleShelf hangar={data} />} />
              <Route path="people/:id" element={<PersonPage hangar={data} />} />
              <Route path="people/:id/history" element={<HistoryPage hangar={data} />} />
              <Route path="drafts/person/:id" element={<DraftPage hangar={data} />} />
              <Route path="workflows" element={<WorkflowShelf hangar={data} />} />
              <Route path="workflows/:id" element={<WorkflowPage hangar={data} />} />
              <Route path="views" element={<ViewShelf hangar={data} />} />
              <Route path="views/template/:id" element={<TemplatePage hangar={data} />} />
              <Route path="views/:workflow/:name" element={<ViewPage hangar={data} />} />
              <Route path="scenarios" element={<ScenarioShelf hangar={data} />} />
              <Route path="scenarios/:id" element={<ScenarioPage hangar={data} />} />
              <Route path="skills" element={<SkillShelf hangar={data} />} />
              <Route path="skills/:id" element={<SkillPage hangar={data} />} />
              <Route path="starters" element={<StarterShelf hangar={data} />} />
              <Route path="starters/:id" element={<StarterPage hangar={data} />} />
              <Route path="frameworks" element={<FrameworkShelf hangar={data} />} />
              <Route path="frameworks/:id" element={<FrameworkPage hangar={data} />} />
              <Route path="*" element={<NotHere />} />
            </Routes>
          )}
        </div>
      </main>
    </div>
  );
}

// -------------------------------------------------------------- small parts

function Health({ problems, ok = "Passes checks" }: { problems: string[]; ok?: string }) {
  return problems.length === 0 ? (
    <span className="chip ok" title="pa check finds nothing wrong">
      ✓ {ok}
    </span>
  ) : (
    <span className="chip fail" title={problems.join("\n")}>
      ✕ {problems.length} problem{problems.length === 1 ? "" : "s"}
    </span>
  );
}

function Checks({ problems, passed }: { problems: string[]; passed: string }) {
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

function Mark({
  person,
  small,
}: {
  person: Pick<HangarPerson, "kind" | "stand_in" | "initials" | "name">;
  small?: boolean;
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "mark",
        person.kind === "person" && "person",
        person.stand_in && "stand",
        small && "sm",
      )}
    >
      {person.initials || participantSlug(person.name).slice(0, 2).toUpperCase()}
    </span>
  );
}

function KindChip({ person }: { person: HangarPerson }) {
  return person.stand_in ? (
    <span className="chip stand" title="An agent plays this person">
      Stand-in
    </span>
  ) : (
    <span className="chip">{person.kind === "person" ? "Person" : "Agent"}</span>
  );
}

const Builtin = () => (
  <span
    className="chip lock"
    title="Ships with the app. From the next version: duplicate to change."
  >
    <LockIcon aria-hidden="true" /> Built-in
  </span>
);

function Crumb({ shelf, label }: { shelf: string; label: string }) {
  const name = SHELVES.find((s) => s.id === shelf)?.label ?? shelf;
  return (
    <div className="crumb">
      <Link to={hangarPath.shelf(shelf)}>{name}</Link>
      <span aria-hidden="true">/</span>
      <span>{label}</span>
    </div>
  );
}

function Section({
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

function Links({
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

function NotHere() {
  return <p className="empty">There is nothing here. It may have been renamed or removed.</p>;
}

/** A page drawn by the server (a view, a template or a scenario player) in a sandboxed frame. */
function Rendered({
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

const LAYOUT_GROUPS: { layout: string; label: string }[] = [
  { layout: "tree-table", label: "Tables and lists" },
  { layout: "board", label: "Boards" },
  { layout: "detail", label: "Cards" },
  { layout: "form", label: "Forms" },
  { layout: "summary", label: "Summaries" },
];
const layoutLabel = (layout: string) =>
  ({ "tree-table": "Table", board: "Board", detail: "Card", form: "Form", summary: "Summary" })[
    layout
  ] ?? layout;
const hostLabel = (host: string) => (host === "chat" ? "in the chat" : "in the canvas");

const byId = <T extends { id: string }>(items: T[]) =>
  new Map(items.map((item) => [item.id, item]));

// ----------------------------------------------------------------- overview

function Overview({ hangar }: { hangar: Hangar }) {
  const failing = (items: { problems: string[] }[]) =>
    items.filter((i) => i.problems.length > 0).length;
  const live = hangar.people.filter((p) => p.backing === "session").length;
  const tiles: { shelf: string; label: string; n: number; sub: string; bad: number; ok: string }[] =
    [
      {
        shelf: "people",
        label: "People and agents",
        n: hangar.people.length,
        sub: `${live} answer live, ${hangar.people.length - live} from a script. ${hangar.people.filter((p) => p.stand_in).length} stand-in.`,
        bad: failing(hangar.people),
        ok: "All pass checks",
      },
      {
        shelf: "workflows",
        label: "Workflows",
        n: hangar.workflows.length,
        sub: "Kinds of work, each with steps, records and views.",
        bad: failing(hangar.workflows),
        ok: "All pass checks",
      },
      {
        shelf: "views",
        label: "Views",
        n: hangar.views.length + hangar.templates.length,
        sub: `${hangar.views.length} inside workflows, ${hangar.templates.length} standalone templates.`,
        bad: 0,
        ok: "All draw",
      },
      {
        shelf: "scenarios",
        label: "Scenarios",
        n: hangar.scenarios.length,
        sub: "Scripted runs with invented data.",
        bad: hangar.scenarios.filter((s) => s.error || s.problems.length > 0).length,
        ok: "All play through",
      },
    ];
  return (
    <>
      <div>
        <h1>What people can fly today</h1>
        <p className="sub">
          Everything here is a file in the app's folder. This is how each one looks, what it is made
          of, and what uses it.
        </p>
      </div>
      <div className="grid4">
        {tiles.map((tile) => (
          <Link
            key={tile.shelf}
            to={hangarPath.shelf(tile.shelf)}
            className="card"
            data-testid={`hangar-tile-${tile.shelf}`}
          >
            <span className="lab">{tile.label}</span>
            <span className="big">{tile.n}</span>
            <span className="sub">{tile.sub}</span>
            <span>
              {tile.bad === 0 ? (
                <span className="chip ok">✓ {tile.ok}</span>
              ) : (
                <span className="chip fail">✕ {tile.bad} need fixing</span>
              )}
            </span>
          </Link>
        ))}
      </div>
      <div className="grid3">
        {(
          [
            [
              "skills",
              "Skills",
              hangar.skills.length,
              "What the agent is taught. Workflows are skills too.",
            ],
            [
              "starters",
              "Starters",
              hangar.starters.length,
              "The Library's canned sessions: how people start work.",
            ],
            [
              "frameworks",
              "Frameworks",
              hangar.frameworks.length,
              "How deep a piece of thinking must go.",
            ],
          ] as const
        ).map(([shelf, label, n, sub]) => (
          <Link key={shelf} to={hangarPath.shelf(shelf)} className="card">
            <div className="row">
              <span className="ct">{label}</span>
              <span className="sp" />
              <span className="chip">{n}</span>
            </div>
            <span className="sub">{sub}</span>
          </Link>
        ))}
      </div>
      <div className="grid2">
        <Section title="Build something">
          <p className="sub">
            Each build is a guided session with Aviator, on a draft nobody else sees until you
            publish it. You can stop and come back.
          </p>
          <div className="row">
            <NewPersonButton />
            <span className="lab">Workflows, scenarios and skills come next.</span>
          </div>
        </Section>
        <Section title="In progress">
          {hangar.drafts.length === 0 ? (
            <p className="lab">No drafts.</p>
          ) : (
            hangar.drafts.map((draft) => <DraftCard key={draft.id} draft={draft} />)
          )}
        </Section>
      </div>
      <Section title="How the pieces fit">
        <p style={{ lineHeight: 2 }}>
          A <span className="chip">Starter</span> starts a{" "}
          <span className="chip build">Workflow</span>, which draws{" "}
          <span className="chip">Views</span> over its records and may call{" "}
          <span className="chip">People and agents</span>. A <span className="chip">Scenario</span>{" "}
          is a scripted run of a workflow with a cast and invented data. All of it is taught to the
          agent by <span className="chip">Skills</span>.
        </p>
      </Section>
    </>
  );
}

// ------------------------------------------------------------------- people

function PersonCard({ person }: { person: HangarPerson }) {
  const used = person.used_in.workflows.length;
  return (
    <Link to={hangarPath.person(person.id)} className="card" data-testid="hangar-person-card">
      <div className="row">
        <Mark person={person} />
        <b>{person.name}</b>
        <KindChip person={person} />
        <span className="sp" />
        <Health problems={person.problems} ok="Healthy" />
      </div>
      <span className="sub">{person.role}</span>
      {person.call_for && <span className="lab">Call for: {person.call_for}</span>}
      <div className="row">
        <span className="chip info">
          Answers {person.backing === "script" ? "from a script" : "live, in character"}
        </span>
        <span className="chip">
          Used in {used} workflow{used === 1 ? "" : "s"}
        </span>
      </div>
    </Link>
  );
}

function PeopleShelf({ hangar }: { hangar: Hangar }) {
  return (
    <>
      <div className="row">
        <div className="min-w-0 flex-1">
          <h1>People and agents</h1>
          <p className="sub">
            Who Aviator can bring into a conversation. Square marks are agents, round marks are
            people, and a dashed edge is an agent standing in for a real person.
          </p>
        </div>
        <NewPersonButton />
      </div>
      <div className="grid2">
        {hangar.people.map((person) => (
          <PersonCard key={person.id} person={person} />
        ))}
        {hangar.drafts
          .filter((d) => d.action === "new")
          .map((draft) => (
            <DraftCard key={draft.id} draft={draft} />
          ))}
      </div>
    </>
  );
}

function PersonPage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  // A chat turn only knows the name, so its wrench links by name.
  const person = hangar.people.find((p) => p.id === id || participantSlug(p.name) === id);
  if (!person) return <NotHere />;
  const workflows = byId(hangar.workflows);
  const starters = byId(hangar.starters);
  const isPerson = person.kind === "person";
  return (
    <>
      <Crumb shelf="people" label={person.name} />
      <div className="row">
        <Mark person={person} />
        <h1>{person.name}</h1>
        <KindChip person={person} />
        <Health problems={person.problems} />
        <span className="sp" />
        <PersonActions hangar={hangar} id={person.id} name={person.name} />
      </div>
      <div className="halves">
        <div className="flex flex-col gap-3.5">
          <Section title={`How ${isPerson ? "they appear" : "it appears"} when flying`}>
            <ParticipantTurnBlock
              hangarLink={false}
              turn={{
                name: person.name,
                kind: person.kind,
                role: person.role,
                standIn: person.stand_in,
                sessionId: null,
                body: "",
              }}
            >
              {person.sample ? (
                person.sample.text
              ) : (
                <span className="lab">They have not spoken in a scenario yet.</span>
              )}
            </ParticipantTurnBlock>
            {person.sample && (
              <p className="lab">
                A real line from the scenario{" "}
                <Link className="link" to={hangarPath.scenario(person.sample.scenario)}>
                  {hangar.scenarios.find((s) => s.id === person.sample?.scenario)?.title ??
                    person.sample.scenario}
                </Link>
                .
              </p>
            )}
            <div className="row">
              <span className="lab">In the Session panel:</span>
              <Mark person={person} small />
              <span>{person.name}</span>
              <span className="lab">{person.role}</span>
            </div>
          </Section>
          <Section title="Used in">
            <Links
              items={person.used_in.workflows.map((wid) => ({
                to: hangarPath.workflow(wid),
                label: workflows.get(wid)?.title ?? wid,
                note: "workflow",
              }))}
              empty="No workflow names them. They can still be called from any session."
            />
            <Links
              items={person.used_in.starters.map((sid) => ({
                to: hangarPath.starter(sid),
                label: starters.get(sid)?.title ?? sid,
                note: "starter",
              }))}
              empty=""
            />
          </Section>
          <Section title="Checks">
            <Checks
              problems={person.problems}
              passed="Every required line is there and the shape is right."
            />
          </Section>
        </div>
        <Section title={`What ${isPerson ? "they are" : "it is"} made of`}>
          <dl className="kv">
            <dt>Name</dt>
            <dd>{person.name}</dd>
            <dt>Id</dt>
            <dd className="path">{person.id}</dd>
            <dt>Kind</dt>
            <dd>{isPerson ? "Person" : "Agent"}</dd>
            {isPerson && (
              <>
                <dt>Stand-in</dt>
                <dd>
                  {person.stand_in ? "Yes" : "No"}{" "}
                  <span className="chip lock">Required for a person</span>
                </dd>
              </>
            )}
            <dt>Role</dt>
            <dd>{person.role}</dd>
            <dt>Answers</dt>
            <dd>
              {person.backing === "script"
                ? "Fixed answers written in the file"
                : "Live, from the brief below, in a session you can open"}
            </dd>
            <dt>Call for</dt>
            <dd>{person.call_for || <span className="lab">Not set</span>}</dd>
            <dt>Skills</dt>
            <dd>
              {person.skills ? (
                person.skills.map((s) => (
                  <Link key={s} className="link mr-2" to={hangarPath.skill(s)}>
                    {s}
                  </Link>
                ))
              ) : (
                <>
                  Every bundled skill <span className="lab">(a skills line can narrow it)</span>
                </>
              )}
            </dd>
          </dl>
          <span className="lab">{person.backing === "script" ? "Script" : "Brief"}</span>
          <pre className="text tall">{unwrap(person.brief)}</pre>
          <span className="path">{person.path}</span>
        </Section>
      </div>
    </>
  );
}

// ---------------------------------------------------------------- workflows

function WorkflowCard({ workflow, hangar }: { workflow: HangarWorkflow; hangar: Hangar }) {
  const people = byId(hangar.people);
  return (
    <Link to={hangarPath.workflow(workflow.id)} className="card" data-testid="hangar-workflow-card">
      <div className="row">
        <b>{workflow.title}</b>
        {workflow.builtin && <Builtin />}
        <span className="sp" />
        <Health problems={workflow.problems} ok="Passes" />
      </div>
      <span className="sub">{workflow.summary}</span>
      <div className="row">
        <span className="chip">{workflow.steps.length} steps</span>
        <span className="chip">{workflow.views.length} views</span>
        <span className="chip">
          {workflow.participants.length
            ? `${workflow.participants.length} can be called`
            : "No one else called"}
        </span>
        <span className="chip">{workflow.script ? "1 scenario" : "No scenario"}</span>
        <span className="row" style={{ gap: 3 }}>
          {workflow.participants.map((pid) => {
            const p = people.get(pid);
            return p ? <Mark key={pid} person={p} small /> : null;
          })}
        </span>
      </div>
      <span className="path">{workflow.path}</span>
    </Link>
  );
}

function WorkflowShelf({ hangar }: { hangar: Hangar }) {
  return (
    <>
      <div>
        <h1>Workflows</h1>
        <p className="sub">
          Each kind of work a person can do with Aviator. The lock means it ships with the app.
        </p>
      </div>
      <div className="grid2">
        {hangar.workflows.map((w) => (
          <WorkflowCard key={w.id} workflow={w} hangar={hangar} />
        ))}
      </div>
    </>
  );
}

function ViewThumb({ view }: { view: HangarView }) {
  return (
    <Link
      to={hangarPath.view(view.workflow, view.name)}
      className="card"
      style={{ padding: 8 }}
      data-testid="hangar-view-card"
    >
      <Rendered path={viewPagePath(view)} title={view.title} thumb host={view.host} />
      <b className="text-[13px]">{view.title}</b>
      <span className="lab">
        {layoutLabel(view.layout)} · {hostLabel(view.host)}
      </span>
    </Link>
  );
}

function WorkflowPage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  const workflow = hangar.workflows.find((w) => w.id === id);
  if (!workflow) return <NotHere />;
  const people = byId(hangar.people);
  const starters = byId(hangar.starters);
  const skills = hangar.skills.filter((s) => s.used_by.includes(workflow.id));
  return (
    <>
      <Crumb shelf="workflows" label={workflow.title} />
      <div className="row">
        <h1>{workflow.title}</h1>
        {workflow.builtin && <Builtin />}
        <Health problems={workflow.problems} ok="All checks pass" />
        <span className="sp" />
        {workflow.script && (
          <Link className="link" to={hangarPath.scenario(workflow.id)}>
            Play its scenario
          </Link>
        )}
      </div>
      <p className="sub">{workflow.summary}</p>
      <Section title="Steps, as the Session panel shows them">
        <div className="steps">
          {workflow.steps.map((step) => (
            <span key={step}>{step}</span>
          ))}
        </div>
        {workflow.progress?.noun && (
          <p className="lab">
            Progress counts {workflow.progress.noun} that are {workflow.progress.label ?? "done"}.
          </p>
        )}
      </Section>
      <Section
        title="Views, drawn from the scenario's sample data"
        aside={
          <Link className="link text-xs" to={hangarPath.shelf("views")}>
            All views
          </Link>
        }
      >
        <div className="grid4">
          {workflow.views.map((view) => (
            <ViewThumb key={view.key} view={view} />
          ))}
        </div>
      </Section>
      <div className="grid3">
        <Section title="Who can be called">
          {workflow.participants.length === 0 ? (
            <p className="lab">Nobody else. Aviator works alone.</p>
          ) : (
            <ul className="plain">
              {workflow.participants.map((pid) => {
                const p = people.get(pid);
                return (
                  <li key={pid} className="row">
                    {p && <Mark person={p} small />}
                    <Link className="link" to={hangarPath.person(pid)}>
                      {p?.name ?? pid}
                    </Link>
                    {!p && <span className="chip fail">Not on the roster</span>}
                  </li>
                );
              })}
            </ul>
          )}
        </Section>
        <Section title="How people start it">
          <Links
            items={workflow.starters.map((sid) => ({
              to: hangarPath.starter(sid),
              label: starters.get(sid)?.title ?? sid,
              note: "starter in the Library",
            }))}
            empty="No starter mentions it."
          />
          {workflow.launchers.map((l) => (
            <p key={l.label} className="text-[13px]">
              Button on{" "}
              {l.on === "markdown"
                ? "any markdown file"
                : l.on === "any"
                  ? "any file"
                  : `${l.on} files`}
              : “{l.label}”
            </p>
          ))}
        </Section>
        <Section title="Records it keeps">
          {workflow.records.map((r) => (
            <p key={r.name} className="text-[13px]">
              <b>{r.name}</b>: {r.fields.map((f) => f.name).join(", ")}
            </p>
          ))}
          {workflow.records.length === 0 && <p className="lab">No records.</p>}
        </Section>
      </div>
      <div className="grid2">
        <Section title="Checks">
          <Checks
            problems={workflow.problems}
            passed="pa check passes: views, records, buttons, cast and script agree."
          />
        </Section>
        <Section title="What it is made of">
          <dl className="kv">
            <dt>Folder</dt>
            <dd className="path">{workflow.path}</dd>
            <dt>Instructions</dt>
            <dd className="path">{workflow.path}SKILL.md</dd>
            <dt>Scenario</dt>
            <dd>
              {workflow.script ? (
                <Link className="link" to={hangarPath.scenario(workflow.id)}>
                  {workflow.script.title}
                </Link>
              ) : (
                "None"
              )}
            </dd>
            <dt>Skills it uses</dt>
            <dd>
              {skills.length === 0
                ? "None named"
                : skills.map((s) => (
                    <Link key={s.id} className="link mr-2" to={hangarPath.skill(s.id)}>
                      {s.id}
                    </Link>
                  ))}
            </dd>
          </dl>
        </Section>
      </div>
    </>
  );
}

// -------------------------------------------------------------------- views

function ViewShelf({ hangar }: { hangar: Hangar }) {
  const workflows = byId(hangar.workflows);
  return (
    <>
      <div>
        <h1>Views</h1>
        <p className="sub">
          Everything a user can be shown, drawn from sample data. Grouped by layout, so a builder
          reuses a layout before inventing one.
        </p>
      </div>
      {LAYOUT_GROUPS.map((group) => {
        const views = hangar.views.filter((v) => v.layout === group.layout);
        if (views.length === 0) return null;
        return (
          <Section key={group.layout} title={`${group.label} · ${views.length}`}>
            <div className="grid4">
              {views.map((view) => (
                <div key={view.key} className="flex min-w-0 flex-col gap-1">
                  <ViewThumb view={view} />
                  <span className="lab">{workflows.get(view.workflow)?.title}</span>
                </div>
              ))}
            </div>
          </Section>
        );
      })}
      <Section title={`Standalone templates · ${hangar.templates.length}`}>
        <div className="grid4">
          {hangar.templates.map((t) => (
            <Link
              key={t.id}
              to={hangarPath.template(t.id)}
              className="card"
              style={{ padding: 8 }}
              data-testid="hangar-template-card"
            >
              <Rendered path={templatePagePath(t.id)} title={t.title} thumb />
              <b className="text-[13px]">{t.title}</b>
              <span className="lab">Template</span>
            </Link>
          ))}
        </div>
      </Section>
    </>
  );
}

function ViewPage({ hangar }: { hangar: Hangar }) {
  const { workflow: wid = "", name = "" } = useParams<{ workflow: string; name: string }>();
  const view = hangar.views.find((v) => v.workflow === wid && v.name === name);
  if (!view) return <NotHere />;
  const workflow = hangar.workflows.find((w) => w.id === wid);
  return (
    <>
      <Crumb shelf="views" label={view.title} />
      <div className="row">
        <h1>{view.title}</h1>
        <span className="chip">{layoutLabel(view.layout)}</span>
        <span className="chip">Shown {hostLabel(view.host)}</span>
      </div>
      <div className="halves" style={{ gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)" }}>
        <Section title="How it looks when flying, over the scenario's sample data">
          <div style={view.host === "chat" ? { maxWidth: 720 } : undefined}>
            <Rendered
              path={viewPagePath(view)}
              title={view.title}
              height={view.host === "chat" ? 520 : 640}
            />
          </div>
          <p className="lab">Buttons here do nothing: there is no conversation behind it.</p>
        </Section>
        <Section title="What it is made of">
          <dl className="kv">
            <dt>Layout</dt>
            <dd>{layoutLabel(view.layout)}</dd>
            <dt>Shown</dt>
            <dd>
              {view.host === "chat" ? "In the chat, as a widget" : "In the canvas beside the chat"}
            </dd>
            <dt>Heading</dt>
            <dd>{view.heading || <span className="lab">None</span>}</dd>
            <dt>Buttons</dt>
            <dd>{view.actions}</dd>
            <dt>Name</dt>
            <dd className="path">{view.name}</dd>
          </dl>
          <span className="path">{view.path}</span>
          <span className="lab">Used in</span>
          <Links
            items={
              workflow
                ? [
                    {
                      to: hangarPath.workflow(workflow.id),
                      label: workflow.title,
                      note: "workflow",
                    },
                  ]
                : []
            }
            empty="No workflow."
          />
          {workflow?.script && (
            <Links
              items={[
                {
                  to: hangarPath.scenario(workflow.id),
                  label: workflow.script.title,
                  note: "scenario",
                },
              ]}
              empty=""
            />
          )}
        </Section>
      </div>
    </>
  );
}

function TemplatePage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  const template = hangar.templates.find((t) => t.id === id);
  if (!template) return <NotHere />;
  const starters = byId(hangar.starters);
  return (
    <>
      <Crumb shelf="views" label={template.title} />
      <div className="row">
        <h1>{template.title}</h1>
        <span className="chip">Standalone template</span>
      </div>
      <div className="halves" style={{ gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)" }}>
        <Section title="How it looks when flying, with its example content">
          <Rendered path={templatePagePath(template.id)} title={template.title} height={640} />
        </Section>
        <Section title="What it is made of">
          <p>{template.description}</p>
          <span className="path">workspace/{template.path}</span>
          <span className="lab">Used by</span>
          <Links
            items={template.starters.map((sid) => ({
              to: hangarPath.starter(sid),
              label: starters.get(sid)?.title ?? sid,
              note: "starter",
            }))}
            empty="No starter names it. Anyone can use it from the Library."
          />
        </Section>
      </div>
    </>
  );
}

// ---------------------------------------------------------------- scenarios

function ScenarioShelf({ hangar }: { hangar: Hangar }) {
  const people = byId(hangar.people);
  const workflows = byId(hangar.workflows);
  return (
    <>
      <div>
        <h1>Scenarios</h1>
        <p className="sub">
          Scripted runs of a workflow with a cast and invented data, for demos that must go the same
          way every time.
        </p>
      </div>
      <div className="grid2">
        {hangar.scenarios.map((s) => (
          <Link
            key={s.id}
            to={hangarPath.scenario(s.id)}
            className="card"
            data-testid="hangar-scenario-card"
          >
            <div className="row">
              <b>{s.title}</b>
              <span className="sp" />
              {s.error || s.problems.length ? (
                <span className="chip fail">✕ Does not play through</span>
              ) : (
                <span className="chip ok">✓ Plays through · {s.steps} steps</span>
              )}
            </div>
            <span className="lab">Runs: {workflows.get(s.workflow)?.title ?? s.workflow}</span>
            <div className="row" style={{ gap: 4 }}>
              <span className="lab">Cast:</span>
              {s.cast.length === 0 && <span className="lab">Aviator only</span>}
              {s.cast.map((pid) => {
                const p = people.get(pid);
                return p ? <Mark key={pid} person={p} small /> : null;
              })}
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}

function ScenarioPage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  const scenario = hangar.scenarios.find((s) => s.id === id);
  if (!scenario) return <NotHere />;
  const people = byId(hangar.people);
  const workflow = hangar.workflows.find((w) => w.id === scenario.workflow);
  const broken = Boolean(scenario.error) || scenario.problems.length > 0;
  return (
    <>
      <Crumb shelf="scenarios" label={scenario.title} />
      <div className="row">
        <h1>{scenario.title}</h1>
        {broken ? (
          <span className="chip fail">✕ Does not play through</span>
        ) : (
          <span className="chip ok">✓ Plays through · {scenario.steps} steps</span>
        )}
        {workflow && (
          <Link className="chip build" to={hangarPath.workflow(workflow.id)}>
            Runs: {workflow.title}
          </Link>
        )}
      </div>
      <Section title="The player, as it runs in a demo">
        <Rendered
          path={previewPagePath(scenario.id)}
          title={`${scenario.title} preview`}
          height={760}
        />
        <p className="lab">Press Next to step through. Nothing reaches an agent.</p>
      </Section>
      <div className="halves" style={{ gridTemplateColumns: "minmax(0, 3fr) minmax(0, 2fr)" }}>
        <Section title="Screenplay · plain text">
          <pre className="text tall" data-testid="hangar-screenplay">
            {unwrap(scenario.text)}
          </pre>
          <span className="path">{scenario.path}</span>
        </Section>
        <div className="flex flex-col gap-3.5">
          <Section title="Cast and data">
            <ul className="plain">
              {scenario.cast.map((pid) => {
                const p = people.get(pid);
                return (
                  <li key={pid} className="row">
                    {p && <Mark person={p} small />}
                    <Link className="link" to={hangarPath.person(pid)}>
                      {p?.name ?? pid}
                    </Link>
                    {p && <span className="lab">{p.role}</span>}
                  </li>
                );
              })}
            </ul>
            {scenario.fixtures.map((f) => (
              <span key={f} className="path">
                {f}
              </span>
            ))}
          </Section>
          {(scenario.error || scenario.problems.length > 0) && (
            <Section title="Checks">
              <Checks
                problems={[...(scenario.error ? [scenario.error] : []), ...scenario.problems]}
                passed=""
              />
            </Section>
          )}
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------- skills, starters, frameworks

function SkillShelf({ hangar }: { hangar: Hangar }) {
  const groups: [string, boolean][] = [
    ["Workflow skills", true],
    ["Other skills", false],
  ];
  return (
    <>
      <div>
        <h1>Skills</h1>
        <p className="sub">
          What the agent is taught. Every session gets all of them. A workflow is a skill with
          steps, records and views.
        </p>
      </div>
      {groups.map(([label, isWorkflow]) => (
        <Section key={label} title={label}>
          <div className="grid2">
            {hangar.skills
              .filter((s) => s.workflow === isWorkflow)
              .map((s) => (
                <Link key={s.id} to={hangarPath.skill(s.id)} className="card">
                  <div className="row">
                    <b className="font-mono text-[13px]">{s.id}</b>
                    <span className="sp" />
                    <span className="chip">Used by {s.used_by.length}</span>
                  </div>
                  <span className="sub line-clamp-2">{s.description}</span>
                </Link>
              ))}
          </div>
        </Section>
      ))}
    </>
  );
}

function SkillPage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  const skill = hangar.skills.find((s) => s.id === id);
  if (!skill) return <NotHere />;
  const uses = hangar.skills.filter((s) => s.used_by.includes(skill.id));
  const frameworks = hangar.frameworks.filter((f) => f.used_by.includes(skill.id));
  return (
    <>
      <Crumb shelf="skills" label={skill.id} />
      <div className="row">
        <h1 className="font-mono">{skill.id}</h1>
        {skill.workflow && (
          <Link className="chip build" to={hangarPath.workflow(skill.id)}>
            A workflow
          </Link>
        )}
      </div>
      <p className="sub">{skill.description}</p>
      <div className="grid3">
        <Section title="Used by">
          <Links
            items={skill.used_by.map((sid) => ({ to: hangarPath.skill(sid), label: sid }))}
            empty="No other skill names it."
          />
        </Section>
        <Section title="Uses">
          <Links
            items={[
              ...uses.map((s) => ({ to: hangarPath.skill(s.id), label: s.id, note: "skill" })),
              ...frameworks.map((f) => ({
                to: hangarPath.framework(f.id),
                label: f.title,
                note: "framework",
              })),
            ]}
            empty="Nothing else."
          />
        </Section>
        <Section title="Files">
          <ul className="plain">
            {skill.files.map((f) => (
              <li key={f} className="path">
                {f}
              </li>
            ))}
          </ul>
          <span className="path">{skill.path}</span>
        </Section>
      </div>
    </>
  );
}

function StarterShelf({ hangar }: { hangar: Hangar }) {
  const workflows = byId(hangar.workflows);
  return (
    <>
      <div>
        <h1>Starters</h1>
        <p className="sub">
          The canned sessions in the Library. Each opens the composer with its prompt filled in;
          nothing is sent by itself.
        </p>
      </div>
      <div className="grid2">
        {hangar.starters.map((s) => (
          <Link
            key={s.id}
            to={hangarPath.starter(s.id)}
            className="card"
            data-testid="hangar-starter-card"
          >
            <b>{s.title}</b>
            <span className="sub">{s.description}</span>
            <div className="row">
              {s.workflows.map((w) => (
                <span key={w} className="chip build">
                  {workflows.get(w)?.title ?? w}
                </span>
              ))}
              {s.template && <span className="chip">Template: {s.template}</span>}
              {s.fields.length > 0 && (
                <span className="chip">
                  {s.fields.length} blank{s.fields.length === 1 ? "" : "s"} to fill
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}

function StarterPage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  const starter = hangar.starters.find((s) => s.id === id);
  if (!starter) return <NotHere />;
  const workflows = byId(hangar.workflows);
  const people = byId(hangar.people);
  const template = starter.template
    ? hangar.templates.find((t) => t.id === starter.template)
    : undefined;
  return (
    <>
      <Crumb shelf="starters" label={starter.title} />
      <h1>{starter.title}</h1>
      <div className="halves">
        <Section title="How it looks in the Library">
          <div className="card" style={{ background: "var(--pa-surface)" }}>
            <b>{starter.title}</b>
            <span className="sub">{starter.description}</span>
            {starter.fields.map((f) => (
              <label key={f.name} className="flex flex-col gap-1">
                <span className="lab">{f.name.replace(/[-_]/g, " ")}</span>
                <span className="rounded border border-[var(--pa-line-strong)] px-2 py-1 text-[13px] text-[var(--pa-ink-3)]">
                  {f.hint || " "}
                </span>
              </label>
            ))}
            <span>
              <span
                className="chip"
                style={{ background: "var(--pa-navy)", color: "var(--pa-on-navy)" }}
              >
                Open in composer
              </span>
            </span>
          </div>
        </Section>
        <Section title="What it is made of">
          <span className="lab">Prompt</span>
          <pre className="text">{unwrap(starter.prompt)}</pre>
          <span className="path">workspace/{starter.path}</span>
          <span className="lab">Uses</span>
          <Links
            items={[
              ...starter.workflows.map((w) => ({
                to: hangarPath.workflow(w),
                label: workflows.get(w)?.title ?? w,
                note: "workflow",
              })),
              ...starter.participants.map((p) => ({
                to: hangarPath.person(p),
                label: people.get(p)?.name ?? p,
                note: "cast",
              })),
              ...(template
                ? [
                    {
                      to: hangarPath.template(template.id),
                      label: template.title,
                      note: "template",
                    },
                  ]
                : []),
            ]}
            empty="Nothing else: a free prompt."
          />
        </Section>
      </div>
    </>
  );
}

function FrameworkShelf({ hangar }: { hangar: Hangar }) {
  return (
    <>
      <div>
        <h1>Frameworks</h1>
        <p className="sub">
          How deep and how broad a piece of thinking has to go before it moves on. Skills read these
          files.
        </p>
      </div>
      <div className="grid2">
        {hangar.frameworks.map((f) => (
          <Link key={f.id} to={hangarPath.framework(f.id)} className="card">
            <b>{f.title}</b>
            <span className="lab">Read by: {f.used_by.join(", ") || "no skill yet"}</span>
            <span className="path">{f.path}</span>
          </Link>
        ))}
      </div>
    </>
  );
}

function FrameworkPage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  const framework = hangar.frameworks.find((f) => f.id === id);
  if (!framework) return <NotHere />;
  return (
    <>
      <Crumb shelf="frameworks" label={framework.title} />
      <h1>{framework.title}</h1>
      <div className="halves" style={{ gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)" }}>
        <Section title="The file">
          <pre className="text tall">{unwrap(framework.text)}</pre>
          <span className="path">{framework.path}</span>
        </Section>
        <Section title="Read by">
          <Links
            items={framework.used_by.map((s) => ({
              to: hangarPath.skill(s),
              label: s,
              note: "skill",
            }))}
            empty="No skill reads it yet."
          />
        </Section>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ building

const draftName = (draft: HangarDraft) => draft.person?.name ?? draft.id;
function draftStepLabel(draft: HangarDraft): string {
  if (draft.action === "remove") return "remove";
  const at = draft.step ? BUILD_STEPS.indexOf(draft.step as (typeof BUILD_STEPS)[number]) : -1;
  return at >= 0 ? `${at + 1}/${BUILD_STEPS.length}` : "draft";
}
const ACTION_LABEL = { new: "New", change: "Change", remove: "Removal" } as const;

function NewPersonButton() {
  return (
    <Link
      to={builderSessionLink(buildPrompts.create())}
      className="hangar-btn pri"
      data-testid="hangar-new-person"
    >
      New person or agent
    </Link>
  );
}

function DraftCard({ draft }: { draft: HangarDraft }) {
  return (
    <Link to={hangarPath.draft(draft.id)} className="card draft" data-testid="hangar-draft-card">
      <div className="row">
        {draft.person && (
          <Mark person={{ ...draft.person, initials: draft.person.initials }} small />
        )}
        <b>{draftName(draft)}</b>
        <span className="chip build">{ACTION_LABEL[draft.action]} · draft</span>
        <span className="sp" />
        <span className="lab">{draftStepLabel(draft)}</span>
      </div>
      <span className="lab">Not published. Nobody flying can see this.</span>
    </Link>
  );
}

function ActionError({ error }: { error: unknown }) {
  return error ? (
    <p className="chip fail">{error instanceof Error ? error.message : String(error)}</p>
  ) : null;
}

/** Edit, duplicate, retire and history for a live person. Edits always open a draft. */
function PersonActions({ hangar, id, name }: { hangar: Hangar; id: string; name: string }) {
  const navigate = useNavigate();
  const { startDraft } = useHangarActions();
  const existing = hangar.drafts.find((d) => d.id === id);
  const person = hangar.people.find((p) => p.id === id);
  const inUse = person ? person.used_in.workflows.length + person.used_in.starters.length : 0;
  const open = (remove: boolean) =>
    startDraft.mutate(
      { id, remove },
      {
        onSuccess: () =>
          navigate(remove ? hangarPath.draft(id) : builderSessionLink(buildPrompts.edit(id, name))),
      },
    );
  return (
    <div className="row">
      {existing ? (
        <Link to={hangarPath.draft(id)} className="hangar-btn pri">
          Open the draft
        </Link>
      ) : (
        <button
          type="button"
          className="hangar-btn pri"
          onClick={() => open(false)}
          disabled={startDraft.isPending}
          data-testid="hangar-edit"
        >
          Edit
        </button>
      )}
      <Link to={builderSessionLink(buildPrompts.duplicate(id, name))} className="hangar-btn">
        Duplicate
      </Link>
      <Link to={hangarPath.history(id)} className="hangar-btn">
        History{person && person.history.length > 0 ? ` · ${person.history.length}` : ""}
      </Link>
      {!existing && (
        <button
          type="button"
          className="hangar-btn quiet"
          onClick={() => open(true)}
          disabled={startDraft.isPending}
          title={
            inUse ? `Used in ${inUse} places: removing is blocked until each is changed` : undefined
          }
        >
          Remove…
        </button>
      )}
      <ActionError error={startDraft.error} />
    </div>
  );
}

function StepBar({ step, action }: { step: string | null; action: HangarDraft["action"] }) {
  if (action === "remove") return null;
  const at = step ? BUILD_STEPS.indexOf(step as (typeof BUILD_STEPS)[number]) : -1;
  return (
    <div className="steps" aria-label="Steps of the guided build">
      {BUILD_STEPS.map((label, index) => (
        <span
          key={label}
          className={cn(index < at && "done", index === at && "now")}
          aria-current={index === at ? "step" : undefined}
        >
          {label}
        </span>
      ))}
    </div>
  );
}

function Diff({ before, after }: { before: string; after: string }) {
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

function DraftPage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { publish, discard } = useHangarActions();
  const [summary, setSummary] = useState("");
  const draft = hangar.drafts.find((d) => d.id === id);
  if (!draft) {
    const live = hangar.people.find((p) => p.id === id);
    return live ? (
      <p className="empty">
        There is no draft of {live.name} now: it was published or discarded.{" "}
        <Link className="link" to={hangarPath.person(id)}>
          See {live.name}
        </Link>
      </p>
    ) : (
      <NotHere />
    );
  }
  const workflows = byId(hangar.workflows);
  const starters = byId(hangar.starters);
  const removal = draft.action === "remove";
  const blocked = draft.problems.length > 0;
  const name = draftName(draft);
  const affected = draft.uses.workflows.length + draft.uses.starters.length;
  return (
    <>
      <div className="crumb">
        <Link to={hangarPath.shelf("people")}>People and agents</Link>
        <span aria-hidden="true">/</span>
        <span>Draft: {name}</span>
      </div>
      <div className="row">
        {draft.person && <Mark person={draft.person} />}
        <h1>{removal ? `Remove ${name}` : name}</h1>
        <span className="chip build">{ACTION_LABEL[draft.action]} · draft</span>
        {blocked ? (
          <span className="chip fail">✕ {draft.problems.length} to fix before publishing</span>
        ) : (
          <span className="chip ok">✓ Ready to publish</span>
        )}
      </div>
      <p className="sub">
        Nobody flying sees this until you publish it. Sessions already running keep what they
        started with.
      </p>
      <StepBar step={draft.step} action={draft.action} />
      <div className="halves">
        <div className="flex flex-col gap-3.5">
          {draft.person && (
            <Section title="How they will appear when flying">
              <ParticipantTurnBlock
                hangarLink={false}
                turn={{
                  name: draft.person.name,
                  kind: draft.person.kind,
                  role: draft.person.role,
                  standIn: draft.person.stand_in,
                  sessionId: null,
                  body: "",
                }}
              >
                <span className="lab">
                  {draft.person.call_for
                    ? `Called for ${draft.person.call_for}.`
                    : "No call-for line yet."}
                </span>
              </ParticipantTurnBlock>
            </Section>
          )}
          <Section title="Checks">
            <Checks problems={draft.problems} passed="Every check passes." />
          </Section>
          <Section title={removal ? "What still uses them" : "Who is affected"}>
            {affected === 0 ? (
              <p className="lab">
                {removal
                  ? "Nothing names them."
                  : "No workflow or starter names them. New sessions can call them."}
              </p>
            ) : (
              <>
                <Links
                  items={[
                    ...draft.uses.workflows.map((w) => ({
                      to: hangarPath.workflow(w),
                      label: workflows.get(w)?.title ?? w,
                      note: "workflow",
                    })),
                    ...draft.uses.starters.map((st) => ({
                      to: hangarPath.starter(st),
                      label: starters.get(st)?.title ?? st,
                      note: "starter",
                    })),
                  ]}
                  empty=""
                />
                {!removal && (
                  <p className="lab">Only sessions started after you publish see the change.</p>
                )}
              </>
            )}
          </Section>
        </div>
        <div className="flex flex-col gap-3.5">
          <Section title="Publish">
            {!removal && (
              <label className="flex flex-col gap-1">
                <span className="lab">One line on what changed (kept in History)</span>
                <input
                  className="hangar-input"
                  value={summary}
                  placeholder={
                    draft.action === "new" ? "Added for fraud questions" : "What changed"
                  }
                  onChange={(e) => setSummary(e.target.value)}
                />
              </label>
            )}
            <div className="row">
              <button
                type="button"
                className="hangar-btn pri"
                disabled={blocked || publish.isPending}
                title={blocked ? "Fix every check first" : undefined}
                data-testid="hangar-publish"
                onClick={() =>
                  publish.mutate(
                    {
                      id: draft.id,
                      summary:
                        summary ||
                        (removal
                          ? `removed ${name}`
                          : draft.action === "new"
                            ? `added ${name}`
                            : ""),
                    },
                    {
                      onSuccess: () =>
                        navigate(
                          removal ? hangarPath.shelf("people") : hangarPath.person(draft.id),
                        ),
                    },
                  )
                }
              >
                {removal ? "Remove from the roster" : "Publish"}
              </button>
              {!removal && (
                <Link
                  to={builderSessionLink(buildPrompts.resume(draft.id, draft.step))}
                  className="hangar-btn"
                >
                  Continue with Aviator
                </Link>
              )}
              {!removal && draft.person && (
                <Link
                  to={builderSessionLink(buildPrompts.trial(draft.id, name))}
                  className="hangar-btn"
                >
                  Try them
                </Link>
              )}
              <span className="sp" />
              <button
                type="button"
                className="hangar-btn quiet"
                disabled={discard.isPending}
                onClick={() =>
                  discard.mutate(draft.id, {
                    onSuccess: () =>
                      navigate(
                        draft.action === "new"
                          ? hangarPath.shelf("people")
                          : hangarPath.person(draft.id),
                      ),
                  })
                }
              >
                Discard draft
              </button>
            </div>
            {draft.live !== null && !removal && (
              <p className="lab">Publishing keeps the current version in History.</p>
            )}
            <ActionError error={publish.error ?? discard.error} />
          </Section>
          {!removal && (
            <Section title={draft.live === null ? "The new file" : "What changes"}>
              {draft.live === null ? (
                <pre className="text">{draft.text}</pre>
              ) : (
                <Diff before={draft.live} after={draft.text ?? ""} />
              )}
              <span className="path">
                {draft.path} → {draft.target}
              </span>
            </Section>
          )}
        </div>
      </div>
    </>
  );
}

function HistoryPage({ hangar }: { hangar: Hangar }) {
  const { id = "" } = useParams<{ id: string }>();
  const { restore } = useHangarActions();
  const [open, setOpen] = useState<string | null>(null);
  const version = useHangarVersion(id, open);
  const person = hangar.people.find((p) => p.id === id);
  if (!person) return <NotHere />;
  const busy = hangar.drafts.some((d) => d.id === id);
  return (
    <>
      <div className="crumb">
        <Link to={hangarPath.shelf("people")}>People and agents</Link>
        <span aria-hidden="true">/</span>
        <Link to={hangarPath.person(id)}>{person.name}</Link>
        <span aria-hidden="true">/</span>
        <span>History</span>
      </div>
      <h1>{person.name}: earlier versions</h1>
      <p className="sub">
        Every publish keeps the version it replaced. Restoring one makes it live again through the
        same checks, and keeps the version it replaces too.
      </p>
      {busy && (
        <p className="chip build">
          There is a draft in progress. Publish or discard it before restoring.
        </p>
      )}
      <div className="halves">
        <Section
          title={`${person.history.length} earlier version${person.history.length === 1 ? "" : "s"}`}
        >
          {person.history.length === 0 && (
            <p className="lab">Nothing has been published over this version yet.</p>
          )}
          <ul className="plain" data-testid="hangar-history">
            {person.history.map((v) => (
              <li key={v.version} className="row">
                <button
                  type="button"
                  className={cn("link", open === v.version && "font-semibold")}
                  onClick={() => setOpen(v.version)}
                >
                  {new Date(v.at || 0).toLocaleString()}
                </button>
                <span className="lab">{v.summary}</span>
                <span className="sp" />
                <button
                  type="button"
                  className="hangar-btn"
                  disabled={busy || restore.isPending}
                  onClick={() => restore.mutate({ id, version: v.version })}
                >
                  Restore
                </button>
              </li>
            ))}
          </ul>
          <ActionError error={restore.error} />
        </Section>
        <Section title={open ? "That version, against what is live" : "Pick a version to compare"}>
          {open && version.data && <Diff before={version.data.text} after={person.text} />}
        </Section>
      </div>
    </>
  );
}
