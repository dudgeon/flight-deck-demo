# Evals

Prompt text is measured, not argued (D-133). Each suite runs through the real
app on this machine, so the skills, bridge and tools are the ones Geoff flies.
Nothing here uses the Claude API: the agent under test and the judge are
Claude Code (D-02). Run folders go to `evals/runs/` (gitignored); the usage
log keeps each trial's lines in `logs/usage/eval/<suite>/`.

## Routing suite (built)

Does Aviator start a workflow, offer one, or stay out of the way (D-128)?

```bash
python3 evals/routing_suite.py tasks              # what will run, and each task's split
python3 evals/routing_suite.py smoke              # one cheap turn on Haiku: can the app be driven?
python3 evals/routing_suite.py run --split tune --label baseline
python3 evals/routing_suite.py report evals/runs/<run>
python3 evals/routing_suite.py pairs evals/runs/<a> evals/runs/<b>
```

- **Tasks.** Every workflow's `routing.examples` (start, offer, open), plus
  `routing/tasks.json`: near misses across workflows, quick answers, open
  work, cross-workflow offers, and two lifecycle prompts that wait for the
  lifecycle skill. A new workflow brings its own tasks. Each task's split
  (tuning 60%, held out 40%) is fixed by its id.
- **A trial.** A fresh copy of the Workspace project's folder (configuration,
  no data, runs or drafts), a new session in that project on the model under
  test (`--model`, Sonnet by default), the prompt, one turn (`--timeout`,
  300 s). A question card left waiting ends the turn. A thread the turn
  starts is stopped as soon as it appears. Trial sessions are archived.
- **Evidence.** The usage log's lines for the trial (skill loaded, thread
  created, `offer.made`), the files the turn wrote (briefs, runs), and any
  question card. Only when these are silent does the judge (Claude Code on
  Haiku, `--judge-model`; `--no-judge` for code only) read the reply, to tell
  an offer in words from open work or an answer.
- **Passing.** start: the named workflow started. offer: offered, nothing
  started. open and answer: nothing started, nothing offered. A task passes
  on 2 of 3 trials (`--trials`).
- **Output.** `trials.jsonl` (every trial with its evidence), `summary.json`,
  and `report.md`: tasks passed overall, by split and by expected label, a
  table of expected against observed, and every failing trial with its prompt
  and reply.
- **Cost.** About 10 to 30 seconds a turn on Sonnet. 42 runnable tasks × 3
  trials is about an hour; one split with one trial is a few minutes. Trials
  run one at a time, because the eval tag is one file per machine.

**The tuning loop.** Change one thing (a workflow's routing block, the ladder
in `workspace/CLAUDE.md`, the director skill), run the tuning split, read the
failing trials, and keep the change only if the held-out split does not get
worse. Each round, `pairs` puts ten prompts where two runs differ side by
side, which run is which hidden; Geoff picks the better reply in each, and
the key in the same folder tells which run won and whether the judge agreed.

## Not built yet

The persona suite (12 conversations per hero skill with simulated PMs at three
strictness levels) and the coordination suite (multi-thread stories,
including long-haul ones with a forced compaction). See
`docs/product/director-coordination.md`, Part 5.
