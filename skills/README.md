# Bundled skills

Every skill folder here (one with a `SKILL.md`) is available in every
omnigent-slim session, without anything being installed in `~/.claude`.

To add one, drop a folder in here: `skills/<name>/SKILL.md`, plus any files it
references. New sessions pick it up; running sessions keep what they started
with. Deleting a folder removes the skill from sessions started afterwards.

In a session the skill appears as `/<name>`, e.g. `/omnigent-operator`, and
Claude can also pick it up on its own from the skill's `description`.

## How it works

Each folder here has a link in the repository's `.claude/skills/` folder
(`.claude/skills/<name> -> ../../skills/<name>`). Sessions run in
`workspace/`, and Claude Code reads the `.claude/skills/` folders of the
working folder and the folders above it, so it finds them by itself. No
plugin is passed: company managed settings can refuse plugin flags (D-172).
A workflow published from the Hangar into `workspace/.claude/skills/` with
the same name is nearer, so it wins (D-72).

**Adding a skill:** add `skills/<name>/SKILL.md` and its link:

```bash
ln -s ../../skills/<name> .claude/skills/<name>
```

`tests/test_slim_claude_sdk.py` fails if a skill has no link or a link has
no skill.

`omnigent/slim_skills.py` (linking into the terminal harness's plugin
bundle, with `OMNIGENT_SLIM_SKILLS_DIR`) is kept for the terminal harness,
which sessions no longer use.

For writing skills that use Omnigent's viewer, sessions and other tools, see
`docs/skill-writers/`. `omnigent-operator` here is a working example.
