# Writing to the usage log from a skill

Flight Deck keeps a local usage log (`logs/usage/`, spec in
[../product/usage-logging.md](../product/usage-logging.md)). Most skills need
to do nothing: every `pa` command a skill runs is already a line, with its
ids, exit code, time taken, and the run's workflow and session. Every tool
call and every skill loaded is a line too.

Write your own event only for a moment `pa` cannot see.

```
$PA log offer.made workflow=intent-shaping --session <your session id>
$PA log offer.taken workflow=intent-shaping --session <your session id>
$PA log skill.step step=frame workflow=problem-discovery --run <run id>
$PA log skill.outcome result=brief-written workflow=problem-discovery
```

Rules (the writer enforces them, so a mistake is lost rather than leaked):

- The event name is `area.action`, lower case: `offer.made`, `skill.step`.
- Fields are `key=value`, keys in lower snake case. Values are ids, status
  words and numbers. Anything with a space becomes `<text N>` in the log: do
  not pass the person's words, a record's title or a summary.
- `--session`, `--project`, `--workflow`, `--run`, `--scenario`, `--mode`
  set the line's context, which is how lines are grouped later.
- `--show` prints the line as written.
- Logging never fails the command that runs it, and `OMNIGENT_SLIM_USAGE=0`
  turns it off.

Names already in use, so new events can line up with them:

| Event | Written by | Means |
|---|---|---|
| `pa.<command>` | `pa` | A `pa` command ran (`params.exit` is its exit code) |
| `tool.used` | runner | A tool was called; `skill=` when it was Skill |
| `web.page_view`, `web.click`, `web.interaction` | web app | A page shown, a control clicked, a timed interaction |
| `upstream.session_created`, `upstream.turn_end`, `upstream.native_session_usage`, ... | server | Upstream Omnigent's own telemetry events, kept locally |
| `hangar.publish`, `hangar.draft_save`, `hangar.send_to_repo`, ... | server | A change in the Hangar |
| `api.slim_write` | server | Any other change through a slim route |
| `offer.made`, `offer.taken` | skills (proposed) | The director offered a hero skill, and the person took it (AV-1) |

To read it: `$PA usage tail`, `$PA usage summary --since 1d`.
