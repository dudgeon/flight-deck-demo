# Usage logging

Geoff, 21 November 2026: "We plan to use this for testing a lot; I want to
understand how the entire platform is being used. We don't have a mechanism to
save data remotely, but Flight Deck and the associated skills should still
build logs as files in the repo, that can later be aggregated and analyzed,
and eventually could be sent to a remote server."

Walkthrough put to Geoff: https://claude.ai/artifact/7tXLiAF95CZpCp81UKVVMB (offline copy in `docs/decision-artifacts/2026-11-21-usage-log/`).

This page is the design. What is built is marked; the questions UL-1 to UL-3
are answered at the end. Decisions: D-122 to D-127, D-157 and D-158 in
[decisions.md](decisions.md).

## What it answers

- Which parts of the app people use, and which they never reach: pages,
  buttons, the Library, the Hangar, the Inbox.
- Which workflows and skills get started, which steps they reach, where runs
  pause or stop, and which `pa` commands fail.
- What a session costs: turns, failed turns, tokens, dollars.
- For testing: in an eval trial, which skill Aviator loaded, whether it
  started a thread or wrote a brief, and whether anything failed. The routing
  suite's code graders read these lines instead of parsing transcripts.

It does not answer what anyone said or wrote. That stays in the sessions and
the workspace files, where it already is.

## One log, four feeds (built)

```
web app ── upstream analytics sink ──► POST /v1/slim/usage/events ─┐
server ─── upstream telemetry.emit ──► tee_upstream ───────────────┤
           slim route writes ─────────► route_event ───────────────┤──► usagelog.py ──► logs/usage/<day>.jsonl
runner ─── PostToolUse observer ─────► observe_tool ───────────────┤                    logs/usage/eval/<suite>/<day>.jsonl
pa ─────── every command, pa log ────────────────────────────────────┘
```

All four write through one standard-library module,
`skills/view-kit/scripts/usagelog.py`, so the rules below hold whoever writes.

| Feed | What it records | Where it hooks in |
|---|---|---|
| Web app | Page views, clicks, timed interactions (agent runs, loading sessions), each by a stable id, with the page's path | Upstream already instruments the app for a host analytics sink (`web/src/lib/host.ts`); upstream ships none. Ours is `web/src/lib/slimUsage.ts`, installed in `main.tsx`. Batches every 5 seconds and when the page closes |
| Server | Upstream's own telemetry events: session created, stopped, deleted; turn end with status; cumulative tokens and cost; policies | `omnigent/telemetry/client.py` `emit()` calls `tee_upstream` first, before upstream's opt-out check (upstream's remote telemetry stays off) |
| Server | Every change made through a slim route: Hangar draft, publish, restore, Send to repo; Inbox participant messages; projects | One middleware in `omnigent/server/app.py`, mapped in `slim_usage.route_event`. Reads are not logged: the app polls them |
| Runner | `tool.used` for every tool call, with the skill's name when the tool is Skill and the agent type for Task | `_observe_native_file_changes` in `omnigent/runner/app.py`, which already receives every `PostToolUse` |
| `pa` | `pa.<command>` for every command: its ids, exit code and time taken; the run's workflow and session | `pa.py` `main()` |
| Skills | Events a skill writes on purpose: `pa log offer.made workflow=intent-shaping` | `pa log` |

## The line (built, D-123)

One JSON object per line. Field names follow upstream Omnigent's telemetry
record (`omnigent/telemetry/client.py`) so the production team's pipeline can
take them, with what upstream has no slot for in `context` and `params`.

```json
{"schema": "omnigent-slim.usage", "schema_version": 1,
 "event_id": "18421e73849f46f2b73794329761c0db",
 "event_name": "tool.used", "source": "tool",
 "timestamp": "2026-11-21T22:31:04.512Z", "timestamp_ns": 1795300264512000000,
 "installation_id": "9ba3021fb4354e08966e887034dac60b",
 "process_id": "b4eb056dcbc14b5fbcaa354e5de2ff7b",
 "session_id": "conv_8f2c...", "omnigent_version": "bd08c5e61850",
 "operating_system": "Darwin", "level": "ids",
 "context": {"workflow": "intent-shaping", "mode": "flying"},
 "params": {"tool": "Skill", "skill": "intent-shaping"}}
```

- `event_name` is `area.action`, lower case. Areas in use: `web`, `upstream`,
  `hangar`, `api`, `tool`, `pa`, and whatever skills write (`skill`, `offer`).
- `source` is one of `server`, `web`, `pa`, `skill`, `tool`, `eval`.
- `installation_id` is a random id made once per copy of the app
  (`logs/usage/install-id`). It names nobody; it tells the Mac mini's lines
  from the work Mac's when packs are put together.
- `process_id` groups one process's lines, as upstream's per-process
  `session_id` does. `session_id` here is the Omnigent conversation.
- `context` holds the five things lines are grouped by: `project`,
  `workflow`, `run`, `scenario`, `mode` (flying, hangar, demo, eval), and
  `eval` during a trial.
- `schema_version` changes only when a field changes meaning. Adding an event
  or a parameter does not change it.

## Privacy (built, D-124)

Ids and words, never sentences. A parameter can be a number, yes or no, or a
short string with no spaces: an id, a status word, a file name. Anything else
is replaced by `<text N>`, keeping only its length. So a prompt, a record's
title, a document's text or a `pa add --json` payload cannot reach the log
by accident, whoever writes the line. Paths are made relative to the app
folder (`workspace/data/x.json`) or the home folder (`~/notes.md`).

`pa usage check` re-reads every line against the same rules, and
`pa usage pack` leaves out any line that fails them.

Names are the remaining risk: a dataset called `falcon-acquisition.json` says
something on its own. The fingerprint level replaces every name with a short
salted hash (`#3f9a02c1d4`), except a fixed vocabulary (tools, skills,
workflows, pages, status words). It is set per machine
(`OMNIGENT_SLIM_USAGE_LEVEL=fingerprint`) or applied to one pack
(`pa usage pack --fingerprint`). UL-2 asks which to use where.

## Where the files are (built to UL-1's recommendation, D-122)

`<app folder>/logs/usage/<day>.jsonl`: the git checkout on the Mac mini,
`~/flight-deck` on the work Mac. A file rolls to `<day>.2.jsonl` past 20 MB.
Metadata lines are about 400 bytes, so a busy day is a few megabytes.

- `logs/` is gitignored, so nothing is committed by accident.
- Setup's updates (`scripts/install_sync.py`) skip `logs/` like `updates/`, so
  a new download never touches it and the log survives every update.
- `OMNIGENT_SLIM_USAGE_DIR` moves it; `OMNIGENT_SLIM_USAGE=0` turns it off.
  Test runs (`pytest`) stay out of the real log unless a test points it
  somewhere.

## Evals (built, D-126)

The testing plan in [director-coordination.md](director-coordination.md)
(AV-6) grades the routing suite with code: which skill loaded, whether a
thread or brief was made. The usage log is that evidence.

- `pa usage eval start routing r-07 2` tags every line written on this
  machine as that trial until `pa usage eval stop` (a file,
  `logs/usage/eval-tag.json`, so sessions the server starts are tagged too).
  A runner that starts processes itself can set
  `OMNIGENT_SLIM_EVAL=routing/r-07/2` instead.
- Tagged lines go to `logs/usage/eval/<suite>/`, so real use stays clean and
  eval output can be deleted on its own. Summaries leave them out unless
  asked (`--eval`, `--suite routing`).
- A routing grader reads one trial's lines: `tool.used` with `skill=` names
  the skill loaded; `pa.brief` means a thread was briefed; `pa.flow` with its
  `workflow` means a run started; `upstream.turn_end` with `status=failed` is
  a failed turn.
- For the offer the ladder asks for (AV-1), the director skill can write
  `pa log offer.made workflow=<id>` when it offers, which turns that grade
  from a judge's call into code. Added with the routing suite (D-144), in
  `workspace/CLAUDE.md` and the director skill.

## Reading it (built: the CLI)

```
pa usage summary [--since 7d] [--eval | --suite S] [--json]
pa usage tail [-n 20]
pa usage check
pa usage where
```

`summary` prints events by day and source, sessions, turns, tokens and cost,
pages, clicks, workflows started, skills loaded, tools used, `pa` commands
and which failed, and Hangar actions. `--json` gives the same for a notebook.
`GET /v1/slim/usage/summary` returns it to the app, for a Usage page later.

## Leaving the machine (built: packs; D-127)

There is no server to send to, and the app's processes cannot reach one (the
offline guard). So a log leaves a machine as one file a person carries:

```
pa usage pack [--since 30d] [--fingerprint] [--shape upstream]
```

It writes `~/Desktop/flight-deck-usage-<install>-<date>.jsonl.gz`,
re-checking every line. Packs from several machines are put together by
reading them side by side (`installation_id` tells them apart).

When there is a server, an exporter does the same with a network call. The
interface is `usagelog.Exporter.send(batch)`; `FileExporter` is the only one
today. `--shape upstream` already writes upstream's gateway records
(`{"data": {...}, "partition-key": ...}`), so the first remote exporter can
post them to an Omnigent telemetry gateway unchanged. A remote exporter must
be switched on by a person, and the offline guard stays as it is until then.

## For skill writers

`pa` already logs every command a skill runs, so most skills need nothing.
A skill writes its own event only for a moment `pa` cannot see: an offer
made or taken, a step reached without a `pa` command, an outcome. See
[../skill-writers/usage-log.md](../skill-writers/usage-log.md).

## Answered

| | Question | Answer |
|---|---|---|
| UL-1 | Should usage logs go into the repo's git history? | Not yet (D-157). Kept in the app folder's `logs/`, gitignored; a pack is carried by hand |
| UL-2 | What may a pack from the work Mac hold? | Names as written by default; `--fingerprint` when a pack leaves the work Mac (D-158, changeable) |
| UL-3 | Where should the numbers be seen? | `pa usage summary` for now; a Hangar Usage page only if wanted (D-158, changeable) |

## Not yet

- A Usage page in the Hangar, if wanted (D-158).
- `pa log` lines in the hero skills (offer made and taken), with the routing
  suite.
- Retention: nothing is deleted. At metadata sizes that is years of use.
- Never run on the work Mac or with a live Claude session on the Mac mini:
  the tool and upstream feeds are tested with recorded payloads only.
