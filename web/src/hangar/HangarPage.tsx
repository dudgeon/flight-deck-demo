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
import { useEffect, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { ParticipantTurnBlock } from "@/components/chat/ParticipantTurn";
import { Link, useLocation, useNavigate, useParams } from "@/lib/routing";
import { cn } from "@/lib/utils";
import {
  type Hangar,
  type HangarPerson,
  type HangarView,
  type HangarWorkflow,
  BUILD_STEPS,
  aviatorPrompt,
  builderSessionLink,
  draftAvatarUrl,
  useAvatarActions,
  buildPrompts,
  type CastKind,
  type CastSet,
  type HangarDraft,
  type PersonEdit,
  hangarPath,
  participantSlug,
  previewPagePath,
  templatePagePath,
  trialPrompt,
  unwrap,
  useHangar,
  useHangarActions,
  useHangarVersion,
  useSendToRepo,
  viewPagePath,
} from "./hangarApi";
import { AviatorPopover } from "./AviatorPopover";
import { ActionError, Checks, Crumb, Diff, Links, Rendered, SHELF_LABELS, Section } from "./parts";
import { FolderActions, FolderDraftPage, FolderHistory, NewScenarioButton } from "./FolderEditor";
import "./hangar.css";

// ---------------------------------------------------------------- the frame

const SHELVES: { id: string; label: string; icon: LucideIcon; count: (h: Hangar) => number }[] = [
  { id: "people", label: SHELF_LABELS.people, icon: UsersIcon, count: (h) => h.people.length },
  {
    id: "workflows",
    label: SHELF_LABELS.workflows,
    icon: RouteIcon,
    count: (h) => h.workflows.length,
  },
  {
    id: "views",
    label: SHELF_LABELS.views,
    icon: LayoutGridIcon,
    count: (h) => h.views.length + h.templates.length,
  },
  {
    id: "scenarios",
    label: SHELF_LABELS.scenarios,
    icon: PlayIcon,
    count: (h) => h.scenarios.length,
  },
  { id: "skills", label: SHELF_LABELS.skills, icon: SparklesIcon, count: (h) => h.skills.length },
  {
    id: "starters",
    label: SHELF_LABELS.starters,
    icon: FileTextIcon,
    count: (h) => h.starters.length,
  },
  {
    id: "frameworks",
    label: SHELF_LABELS.frameworks,
    icon: CompassIcon,
    count: (h) => h.frameworks.length,
  },
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
      {hangar && hangar.drafts.length + hangar.folder_drafts.length === 0 && (
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
      {hangar?.folder_drafts.map((draft) => (
        <Link
          key={`${draft.kind}/${draft.id}`}
          to={hangarPath.folderDraft(draft.kind, draft.id)}
          className="hangar-nav"
          aria-current={
            pathname === hangarPath.folderDraft(draft.kind, draft.id) ? "page" : undefined
          }
          data-testid="hangar-draft-nav"
        >
          <WrenchIcon aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate">
            {String(draft.manifest.title || draft.id)}
          </span>
          <span className="n">
            {draft.action === "remove"
              ? "remove"
              : draft.problems.length === 0
                ? "ready"
                : draft.kind}
          </span>
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

function FolderDraftRoute({ hangar }: { hangar: Hangar }) {
  const { kind = "", id = "" } = useParams<{ kind: string; id: string }>();
  if (kind !== "scenario" && kind !== "workflow") return <NotHere />;
  return <FolderDraftPage hangar={hangar} kind={kind} id={id} />;
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
              <Route path="drafts/:kind/:id" element={<FolderDraftRoute hangar={data} />} />
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

function Mark({
  person,
  small,
  src,
}: {
  person: Pick<HangarPerson, "kind" | "stand_in" | "initials" | "name"> & {
    avatar?: string | null;
  };
  small?: boolean;
  /** A picture to show instead of the live one (a draft's). */
  src?: string | null;
}) {
  const picture = src === undefined ? person.avatar : src;
  return (
    <span
      aria-hidden="true"
      className={cn(
        "mark",
        person.kind === "person" && "person",
        person.stand_in && "stand",
        small && "sm",
        picture && "pic",
      )}
    >
      {picture ? (
        <img src={picture} alt="" />
      ) : (
        person.initials || participantSlug(person.name).slice(0, 2).toUpperCase()
      )}
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
    title="Ships with the app. Editing it makes a workspace copy that takes over its id."
  >
    <LockIcon aria-hidden="true" /> Built-in
  </span>
);

function NotHere() {
  return <p className="empty">There is nothing here. It may have been renamed or removed.</p>;
}

/** A page drawn by the server (a view, a template or a scenario player) in a sandboxed frame. */

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

/**
 * Published config that is not committed yet would be lost with a fresh download (D-75).
 * On a git copy, "Send to repo" commits it to a new branch and pushes it (D-113).
 */
function RepoNote({ hangar }: { hangar: Hangar }) {
  const repo = hangar.repo;
  const sendToRepo = useSendToRepo();
  const [summary, setSummary] = useState("");
  if (!repo?.git) return null;
  const sent = sendToRepo.data ?? repo.sent ?? null;
  if (repo.uncommitted.length === 0 && !sendToRepo.data) return null;
  const count = repo.count ?? repo.uncommitted.length;
  const link = sent?.pull_request ?? sent?.open_pr ?? null;
  return (
    <Section title="Not in the repo yet">
      {count > 0 && (
        <>
          <p className="lab">
            {count} published file{count === 1 ? " is" : "s are"} in this folder but not committed.
            Send them to the repo so they travel with it. Your folder stays as it is.
          </p>
          <ul className="plain" data-testid="hangar-uncommitted">
            {repo.uncommitted.slice(0, 8).map((path) => (
              <li key={path} className="path">
                workspace/{path}
              </li>
            ))}
            {count > 8 && <li className="lab">and {count - 8} more</li>}
          </ul>
          <form
            className="row"
            onSubmit={(e) => {
              e.preventDefault();
              sendToRepo.mutate(summary.trim(), { onSuccess: () => setSummary("") });
            }}
          >
            <input
              className="hangar-input"
              style={{ flex: 1 }}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="One line on what changed (optional)"
              aria-label="What changed"
            />
            <button
              type="submit"
              className="hangar-btn pri"
              disabled={sendToRepo.isPending}
              data-testid="hangar-send-to-repo"
            >
              {sendToRepo.isPending ? "Sending…" : "Send to repo"}
            </button>
          </form>
          <ActionError error={sendToRepo.error} />
        </>
      )}
      {sent && (
        <p className="lab" data-testid="hangar-sent">
          Last sent {new Date(sent.at).toLocaleString()} as{" "}
          <span className="path">{sent.branch}</span> ({sent.files} file
          {sent.files === 1 ? "" : "s"}).{" "}
          {link ? (
            <a className="link" href={link} target="_blank" rel="noreferrer">
              {sent.pull_request ? "Open the pull request" : "Open a pull request for it"}
            </a>
          ) : (
            "Merge that branch to bring them into the repo."
          )}{" "}
          Once it is merged and this folder is updated (git pull), they drop off this list.
        </p>
      )}
    </Section>
  );
}

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
            Everything is edited on its own page, on a draft nobody else sees until you publish it,
            with Aviator beside you when you want help. You can stop and come back.
          </p>
          <div className="row">
            <NewPersonButton />
            <NewScenarioButton hangar={hangar} />
            <Link className="hangar-btn" to={hangarPath.shelf("workflows")}>
              Change a workflow
            </Link>
          </div>
        </Section>
        <RepoNote hangar={hangar} />
        <Section title="In progress">
          {hangar.drafts.length + hangar.folder_drafts.length === 0 ? (
            <p className="lab">No drafts.</p>
          ) : (
            <>
              {hangar.drafts.map((draft) => (
                <DraftCard key={draft.id} draft={draft} />
              ))}
              {hangar.folder_drafts.map((draft) => (
                <Link
                  key={`${draft.kind}/${draft.id}`}
                  to={hangarPath.folderDraft(draft.kind, draft.id)}
                  className="card draft"
                  data-testid="hangar-draft-card"
                >
                  <div className="row">
                    <b>{String(draft.manifest.title || draft.id)}</b>
                    <span className="chip build">
                      {draft.action === "new"
                        ? "New"
                        : draft.action === "remove"
                          ? "Removal"
                          : "Change"}{" "}
                      · {draft.kind} draft
                    </span>
                  </div>
                  <span className="lab">Not published. Nobody flying can see this.</span>
                </Link>
              ))}
            </>
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
  const editing = hangar.drafts.find((d) => d.id === person.id && d.action !== "remove");
  if (editing) return <PersonEditor key={editing.id} hangar={hangar} draft={editing} />;
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
        <PersonActions hangar={hangar} id={person.id} />
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
          Each kind of work a person can do with Aviator. The lock means it ships with the app:
          editing one makes a workspace copy. For a new kind of work, open the nearest one and
          duplicate it.
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
        {!workflow.builtin && workflow.shipped && (
          <span className="chip build" title="A workspace copy hides the shipped version">
            Workspace copy
          </span>
        )}
        <Health problems={workflow.problems} ok="All checks pass" />
        <span className="sp" />
        {workflow.script && (
          <Link className="link" to={hangarPath.scenario(workflow.id)}>
            Play its scenario
          </Link>
        )}
      </div>
      <p className="sub">{workflow.summary}</p>
      <FolderActions
        hangar={hangar}
        kind="workflow"
        id={workflow.id}
        builtin={workflow.builtin}
        shipped={workflow.shipped}
      />
      <FolderHistory kind="workflow" id={workflow.id} versions={workflow.history ?? []} />
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
        <NewScenarioButton hangar={hangar} />
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
      {scenario.summary && <p className="sub">{scenario.summary}</p>}
      <FolderActions hangar={hangar} kind="scenario" id={scenario.id} builtin={false} />
      <FolderHistory kind="scenario" id={scenario.id} versions={scenario.history ?? []} />
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

/** Ask for a name, start a draft, and open it as the editor. */
function NameForm({
  label,
  duplicateOf,
  testId,
  primary = true,
}: {
  label: string;
  duplicateOf?: string;
  testId?: string;
  primary?: boolean;
}) {
  const navigate = useNavigate();
  const { create } = useHangarActions();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  if (!open) {
    return (
      <button
        type="button"
        className={cn("hangar-btn", primary && "pri")}
        onClick={() => setOpen(true)}
        data-testid={testId}
      >
        {label}
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
          { name: name.trim(), duplicateOf },
          { onSuccess: (draft) => navigate(hangarPath.draft(draft.id)) },
        );
      }}
    >
      <input
        className="hangar-input"
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder={duplicateOf ? "Name of the copy" : "Their name, e.g. Fraud Ops"}
        aria-label="Name"
      />
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

function NewPersonButton() {
  return <NameForm label="New person or agent" testId="hangar-new-person" />;
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

/** Edit, duplicate, retire and history for a live person. Edits always open a draft. */
function PersonActions({ hangar, id }: { hangar: Hangar; id: string }) {
  const navigate = useNavigate();
  const { startDraft } = useHangarActions();
  const existing = hangar.drafts.find((d) => d.id === id);
  const person = hangar.people.find((p) => p.id === id);
  const inUse = person ? person.used_in.workflows.length + person.used_in.starters.length : 0;
  // Edit turns this page into the editor (D-63); a removal has its own page.
  const open = (remove: boolean) =>
    startDraft.mutate(
      { id, remove },
      { onSuccess: () => (remove ? navigate(hangarPath.draft(id)) : undefined) },
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
      <NameForm label="Duplicate" duplicateOf={id} primary={false} />
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

// ------------------------------------------------------------- the editor
//
// D-63 to D-66: Edit turns the page itself into the editor. Every change saves
// to the draft as you type; Publish is the only step that makes it live. The
// writing help and "Try them" are in the Aviator pop-over.

interface PersonForm {
  name: string;
  role: string;
  kind: "agent" | "person";
  backing: "session" | "script";
  call_for: string;
  skills: string[];
  brief: string;
  cast: CastSet;
}

/** Unwrap a person file's brief for the diff, keeping its frontmatter one field per line. */
function unwrapBody(text: string): string {
  const m = /^(---\n[\s\S]*?\n---\n)([\s\S]*)$/.exec(text);
  return m ? m[1] + unwrap(m[2]) : unwrap(text);
}

function formOf(draft: HangarDraft): PersonForm {
  const p = draft.person;
  return {
    name: p?.name ?? "",
    role: p?.role ?? "",
    kind: p?.kind ?? "agent",
    backing: p?.backing ?? "session",
    call_for: p?.call_for ?? "",
    skills: p?.skills ?? [],
    // Shown and saved as flowing paragraphs, which read and edit better than hard wraps.
    brief: unwrap(draft.brief ?? ""),
    cast: draft.cast,
  };
}

function editOf(form: PersonForm): PersonEdit {
  return {
    fields: {
      name: form.name,
      role: form.role,
      kind: form.kind,
      backing: form.backing,
      call_for: form.call_for,
      skills: form.skills,
    },
    brief: form.brief,
    cast: form.cast,
  };
}

function Seg<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: [T, string][];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div className="seg" role="radiogroup" aria-label={label}>
      {options.map(([v, text]) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={value === v}
          onClick={() => onChange(v)}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

function SkillPicker({
  hangar,
  value,
  onChange,
}: {
  hangar: Hangar;
  value: string[];
  onChange: (skills: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const known = byId(hangar.skills);
  const rest = hangar.skills.filter((s) => !value.includes(s.id));
  return (
    <>
      <div className="row tags">
        {value.map((s) => (
          <span key={s} className="tag" title={known.get(s)?.description}>
            {s}
            <button
              type="button"
              aria-label={`Remove ${s}`}
              onClick={() => onChange(value.filter((k) => k !== s))}
            >
              ×
            </button>
          </span>
        ))}
        <button
          type="button"
          className="addtag"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          data-testid="hangar-add-skill"
        >
          + Add a skill
        </button>
      </div>
      {open && (
        <div className="menu" role="listbox" aria-label="Skills">
          {rest.map((s) => (
            <button
              key={s.id}
              type="button"
              role="option"
              aria-selected={false}
              onClick={() => {
                onChange([...value, s.id]);
                setOpen(false);
              }}
            >
              <b>{s.id}</b>
              <small>{s.description}</small>
            </button>
          ))}
        </div>
      )}
      <span className="lab">
        {value.length === 0
          ? "None picked: they answer from their brief alone."
          : "The session that plays them is told to use these when they answer."}
      </span>
    </>
  );
}

const CAST_GROUPS: { kind: CastKind; label: string }[] = [
  { kind: "workflows", label: "Workflows" },
  { kind: "scenarios", label: "Scenarios" },
  { kind: "starters", label: "Starters" },
];

function CastPicker({
  hangar,
  value,
  onChange,
}: {
  hangar: Hangar;
  value: CastSet;
  onChange: (cast: CastSet) => void;
}) {
  const items: Record<CastKind, { id: string; title: string }[]> = {
    workflows: hangar.workflows.map((w) => ({ id: w.id, title: w.title })),
    scenarios: hangar.scenarios.map((s) => ({ id: s.id, title: s.title })),
    starters: hangar.starters.map((s) => ({ id: s.id, title: s.title })),
  };
  return (
    <div className="castpick">
      {CAST_GROUPS.map(({ kind, label }) => (
        <fieldset key={kind}>
          <legend className="lab">{label}</legend>
          {items[kind].map((item) => {
            const on = value[kind].includes(item.id);
            return (
              <label key={item.id}>
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() =>
                    onChange({
                      ...value,
                      [kind]: on
                        ? value[kind].filter((i) => i !== item.id)
                        : [...value[kind], item.id],
                    })
                  }
                />
                <span>{item.title}</span>
              </label>
            );
          })}
        </fieldset>
      ))}
    </div>
  );
}

type SaveState = "idle" | "saving" | "saved" | "error";

/** A picture for them, picked from a file and copied into the draft (D-74). */
function AvatarPicker({
  draft,
  person,
  src,
}: {
  draft: HangarDraft;
  person: Pick<HangarPerson, "kind" | "stand_in" | "initials" | "name">;
  src: string | null;
}) {
  const input = useRef<HTMLInputElement>(null);
  const { set, clear } = useAvatarActions();
  return (
    <div className="field">
      <span>Picture</span>
      <div className="avatarpick">
        <Mark person={person} src={src} />
        <input
          ref={input}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          data-testid="hangar-avatar-file"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) set.mutate({ id: draft.id, file });
            e.target.value = "";
          }}
        />
        <button
          type="button"
          className="hangar-btn"
          onClick={() => input.current?.click()}
          disabled={set.isPending}
          data-testid="hangar-avatar-pick"
        >
          {src ? "Change picture…" : "Choose a picture…"}
        </button>
        {src && (
          <button
            type="button"
            className="hangar-btn quiet"
            onClick={() => clear.mutate(draft.id)}
            disabled={clear.isPending}
          >
            Remove
          </button>
        )}
        <span className="lab">
          {set.isPending
            ? "Copying…"
            : "PNG, JPEG, WebP or GIF under 2 MB. It is copied into the repo when you publish."}
        </span>
      </div>
      <ActionError error={set.error ?? clear.error} />
    </div>
  );
}

function PersonEditor({ hangar, draft }: { hangar: Hangar; draft: HangarDraft }) {
  const navigate = useNavigate();
  const { edit, publish, discard } = useHangarActions();
  const [form, setForm] = useState<PersonForm>(() => formOf(draft));
  const [summary, setSummary] = useState("");
  const [save, setSave] = useState<SaveState>("idle");
  const [pinned, setPinned] = useState(false);
  const dirty = useRef(false);
  const known = useRef(draft.text);

  // Someone else (Aviator) changed the draft: show it, unless an edit is in flight.
  useEffect(() => {
    if (draft.text !== known.current && !dirty.current) setForm(formOf(draft));
    known.current = draft.text;
  }, [draft]);

  function change(patch: Partial<PersonForm>) {
    dirty.current = true;
    setForm((f) => ({ ...f, ...patch }));
  }

  // Save to the draft a moment after the last keystroke.
  const editMutate = edit.mutateAsync;
  useEffect(() => {
    if (!dirty.current) return;
    setSave("saving");
    const timer = window.setTimeout(() => {
      editMutate({ id: draft.id, edit: editOf(form) })
        .then((saved) => {
          known.current = saved.text;
          dirty.current = false;
          setSave("saved");
        })
        .catch(() => setSave("error"));
    }, 600);
    return () => window.clearTimeout(timer);
  }, [form, draft.id, editMutate]);

  const isNew = draft.action === "new";
  const blocked = draft.problems.length > 0 || save === "saving";
  const initials = form.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
  const person = { ...form, initials, stand_in: form.kind === "person" };
  const firstName = form.name.split(/\s+/)[0] || "them";
  const live = hangar.people.find((p) => p.id === draft.id);
  const workflows = byId(hangar.workflows);
  const scenarios = byId(hangar.scenarios);
  const starters = byId(hangar.starters);
  const title = (kind: CastKind, id: string) =>
    (kind === "workflows"
      ? workflows.get(id)?.title
      : kind === "scenarios"
        ? scenarios.get(id)?.title
        : starters.get(id)?.title) ?? id;
  const path = (kind: CastKind, id: string) =>
    kind === "workflows"
      ? hangarPath.workflow(id)
      : kind === "scenarios"
        ? hangarPath.scenario(id)
        : hangarPath.starter(id);
  const castAll = CAST_GROUPS.flatMap(({ kind }) =>
    draft.cast[kind].map((id) => ({
      to: path(kind, id),
      label: title(kind, id),
      note: kind.slice(0, -1),
    })),
  );

  return (
    <div className={cn("editor", pinned && "with-aviator")} data-testid="hangar-editor">
      <Crumb shelf="people" label={form.name || "New person or agent"} />
      <div className="row">
        <Mark person={person} src={draft.person?.avatar ? draftAvatarUrl(draft) : null} />
        <h1>{form.name || "Unnamed"}</h1>
        <span className="chip build">{isNew ? "New" : "Change"} · draft</span>
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
                ? "Not saved: check the connection"
                : ""}
        </span>
        {live && (
          <Link to={hangarPath.history(draft.id)} className="hangar-btn quiet">
            History{live.history.length > 0 ? ` · ${live.history.length}` : ""}
          </Link>
        )}
      </div>
      <p className="sub">
        Edits save to this draft as you type. Nobody flying sees them until you publish, and
        sessions already running keep what they started with.
      </p>
      <div className="halves">
        <div className="flex flex-col gap-3.5">
          <section className="card editing">
            <span className="lab">Who they are</span>
            <div className="grid2">
              <label className="field">
                <span>Name</span>
                <input
                  className="hangar-input"
                  value={form.name}
                  onChange={(e) => change({ name: e.target.value })}
                  data-testid="hangar-field-name"
                />
              </label>
              <label className="field">
                <span>Role</span>
                <input
                  className="hangar-input"
                  value={form.role}
                  onChange={(e) => change({ role: e.target.value })}
                  placeholder="Design lead, Cards"
                  data-testid="hangar-field-role"
                />
              </label>
              <div className="field">
                <span>Kind</span>
                <Seg
                  label="Kind"
                  value={form.kind}
                  options={[
                    ["person", "Person"],
                    ["agent", "Agent"],
                  ]}
                  onChange={(kind) => change({ kind })}
                />
                <span className="lab">
                  {form.kind === "person"
                    ? "A person is always shown as a stand-in."
                    : "An agent speaks as itself."}
                </span>
              </div>
              <div className="field">
                <span>How they answer</span>
                <Seg
                  label="How they answer"
                  value={form.backing}
                  options={[
                    ["session", "Live session"],
                    ["script", "Script"],
                  ]}
                  onChange={(backing) => change({ backing })}
                />
                <span className="lab">
                  {form.backing === "session"
                    ? "A background session plays them from the brief."
                    : "Fixed answers from a ## Script section."}
                </span>
              </div>
            </div>
            <label className="field">
              <span>Call them for</span>
              <input
                className="hangar-input"
                value={form.call_for}
                onChange={(e) => change({ call_for: e.target.value })}
                placeholder="what Aviator should call them in for"
                data-testid="hangar-field-call"
              />
            </label>
            <AvatarPicker
              draft={draft}
              person={person}
              src={draft.person?.avatar ? draftAvatarUrl(draft) : null}
            />
          </section>
          <section className="card editing">
            <div className="row">
              <span className="lab">
                {form.backing === "script"
                  ? "Brief and script"
                  : "Brief · what the session playing them is told"}
              </span>
              <span className="sp" />
              <span className="lab">{form.brief.split(/\s+/).filter(Boolean).length} words</span>
            </div>
            <textarea
              className="hangar-input brief"
              value={form.brief}
              onChange={(e) => change({ brief: e.target.value })}
              spellCheck
              aria-label="Brief"
              data-testid="hangar-field-brief"
            />
          </section>
          <section className="card editing">
            <span className="lab">Skills they bring</span>
            <SkillPicker
              hangar={hangar}
              value={form.skills}
              onChange={(skills) => change({ skills })}
            />
          </section>
          <section className="card editing">
            <span className="lab">Where they can be called</span>
            <CastPicker hangar={hangar} value={form.cast} onChange={(cast) => change({ cast })} />
          </section>
        </div>
        <div className="flex flex-col gap-3.5">
          <Section title="How they will appear when flying">
            <ParticipantTurnBlock
              hangarLink={false}
              turn={{
                name: form.name || "Unnamed",
                kind: form.kind,
                role: form.role,
                standIn: form.kind === "person",
                sessionId: null,
                body: "",
              }}
            >
              <span className="lab">
                {form.call_for ? `Called for ${form.call_for}.` : "No call-for line yet."}
              </span>
            </ParticipantTurnBlock>
          </Section>
          <Section title="Checks">
            <Checks problems={draft.problems} passed="Every check passes." />
          </Section>
          <Section title={isNew ? "The new file" : "What changes"}>
            {isNew ? (
              <pre className="text">{draft.text}</pre>
            ) : (
              <Diff before={unwrapBody(draft.live ?? "")} after={unwrapBody(draft.text ?? "")} />
            )}
            {draft.cast_changes.length > 0 && (
              <ul className="plain" data-testid="hangar-cast-changes">
                {draft.cast_changes.map((c) => (
                  <li key={`${c.kind}/${c.id}`}>
                    <span className={c.change === "add" ? "add" : "del"}>
                      {c.change === "add" ? "+ Added to " : "− Taken out of "}
                    </span>
                    <Link className="link" to={path(c.kind, c.id)}>
                      {title(c.kind, c.id)}
                    </Link>
                    <span className="lab"> · {c.kind.slice(0, -1)}</span>
                  </li>
                ))}
              </ul>
            )}
            <span className="path">
              {draft.path} → {draft.target}
            </span>
          </Section>
          <Section title="Where they will be called">
            <Links
              items={castAll}
              empty="Nowhere in particular. Any session can still call them."
            />
          </Section>
        </div>
      </div>
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
              { id: draft.id, summary: summary || (isNew ? `added ${form.name}` : "") },
              { onSuccess: () => navigate(hangarPath.person(draft.id)) },
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
            discard.mutate(draft.id, {
              onSuccess: () =>
                navigate(isNew ? hangarPath.shelf("people") : hangarPath.person(draft.id)),
            })
          }
        >
          Discard draft
        </button>
        <ActionError error={publish.error ?? discard.error} />
      </div>
      <AviatorPopover
        name={form.name || "this person"}
        workspace={hangar.workspace_dir}
        pinned={pinned}
        onPinnedChange={setPinned}
        sessionId={draft.aviator}
        onSession={(aviator) => edit.mutateAsync({ id: draft.id, edit: { aviator } })}
        firstPrompt={aviatorPrompt(draft, form.name || "this person")}
        trial={{
          tab: "Try them",
          intro: `Ask ${firstName} a real question. The draft answers the way people will meet them when flying. Nothing is published.`,
          placeholder: `Ask ${firstName} a question…`,
          prompt: (q) => trialPrompt(draft.id, form.name || draft.id, q),
        }}
      />
    </div>
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
  if (draft.action !== "remove")
    return <PersonEditor key={draft.id} hangar={hangar} draft={draft} />;
  const workflows = byId(hangar.workflows);
  const starters = byId(hangar.starters);
  const removal = true;
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
