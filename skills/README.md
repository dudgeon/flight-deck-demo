# Bundled skills

Every skill folder here (one with a `SKILL.md`) is available in every
omnigent-slim session, without anything being installed in `~/.claude`.

To add one, drop a folder in here: `skills/<name>/SKILL.md`, plus any files it
references. New sessions pick it up; running sessions keep what they started
with. Deleting a folder removes the skill from sessions started afterwards.

In a session the skill appears as `/<agent>:<name>`, e.g.
`/claude:omnigent-operator` (Claude Code names plugin skills
`<plugin>:<skill>`, and the plugin is named after the session's agent),
and Claude can also pick it up on its own from the skill's `description`.

## How it works

Omnigent already gives every Claude Code session a skill bundle, passed as
`--plugin-dir`, and links its own skills (`build-omnigent`, `workflow`) into
it. `omnigent/slim_skills.py` links the folders here into that same bundle,
called from `_ensure_orchestrator_skills_in_bundle` in
`omnigent/runner/native/orchestration.py` (marked `omnigent-slim:`). An agent's
own skill with the same name wins.

Set `OMNIGENT_SLIM_SKILLS_DIR` to use a different folder.

For writing skills that use Omnigent's viewer, sessions and other tools, see
`docs/skill-writers/`. `omnigent-operator` here is a working example.
